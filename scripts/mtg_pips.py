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
import cardlib

def get_pip_counts(card, include_text=False):
    """Counts mana pips (symbols) for a card, optionally including rules text."""
    counts = Counter()

    # Face 1
    for sym, count in card.cost.allsymbols.items():
        if count > 0:
            counts[sym] += count

    if include_text:
        for cost in card.text.costs:
            for sym, count in cost.allsymbols.items():
                if count > 0:
                    counts[sym] += count

    # B-side
    if card.bside:
        b_counts = get_pip_counts(card.bside, include_text=include_text)
        counts.update(b_counts)

    return counts

def main():
    parser = argparse.ArgumentParser(
        description="Analyze the distribution of mana symbols (pips) in a dataset.",
        epilog='''
This tool counts mana symbols from casting costs and (optionally) rules text.
It provides a breakdown of each symbol's frequency across the filtered card pool.
'''
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (MTGJSON, Scryfall, CSV, XML, MSE, or encoded text). Defaults to stdin (-).')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save the results. If not provided, results print to the console.')

    # Group: Analysis Options
    analysis_group = parser.add_argument_group('Analysis Options')
    analysis_group.add_argument('--include-text', action='store_true',
                                help='Include mana symbols found in rules text (e.g., activation costs).')
    analysis_group.add_argument('--sort', choices=['name', 'count'], default='count',
                                help='Sort results by symbol name or frequency (Default: count).')
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
    filter_group.add_argument('--booster', type=int, default=0, help='Simulate opening N booster packs.')
    filter_group.add_argument('--box', type=int, default=0, help='Simulate opening N booster boxes.')
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
                                  decklist_file=args.deck,
                                  booster=args.booster, box=args.box,
                                  shuffle=args.shuffle, seed=args.seed)

    if args.limit > 0:
        cards = cards[:args.limit]

    if not cards:
        if not args.quiet:
            print("No cards found matching the criteria.", file=sys.stderr)
        return

    # Count pips
    pip_counts = Counter()
    for card in cards:
        pip_counts.update(get_pip_counts(card, include_text=args.include_text))

    total_pips = sum(pip_counts.values())

    # Prepare results
    results = []
    for sym, count in pip_counts.items():
        percent = (count / total_pips * 100) if total_pips > 0 else 0
        results.append({
            'symbol': sym,
            'count': count,
            'percent': percent
        })

    # Sort
    if args.sort == 'name':
        # Custom sort for mana symbols? For now just string
        results.sort(key=lambda x: x['symbol'], reverse=args.reverse)
    else:
        results.sort(key=lambda x: x['count'], reverse=not args.reverse)

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
            writer.writerow(['Symbol', 'Count', 'Percent'])
            for r in results:
                writer.writerow([r['symbol'], r['count'], f"{r['percent']:.2f}"])
        else:
            # Table
            header = ["Symbol", "Count", "Percent", "Frequency"]
            if use_color:
                header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

            rows = [header]
            for r in results:
                # We need to use the encoded version of the symbol for from_mana to work correctly
                encoded_sym = utils.mana_symall_encode.get(r['symbol'], r['symbol'])
                sym_str = utils.from_mana("{" + encoded_sym + "}", ansi_color=use_color)
                count_str = datalib.color_count(r['count'], use_color)
                percent_str = f"{r['percent']:5.1f}%"
                bar = datalib.get_bar_chart(r['percent'], use_color, color=utils.Ansi.get_color_color(r['symbol']))
                rows.append([sym_str, count_str, percent_str, bar])

            datalib.add_separator_row(rows)

            title = "MANA PIP DISTRIBUTION"
            if args.include_text:
                title += " (INCLUDES RULES TEXT)"

            utils.print_header(title, use_color=use_color)
            datalib.printrows(datalib.padrows(rows, aligns=['l', 'r', 'r', 'l']), indent=2)

    finally:
        if args.outfile:
            output_f.close()

    if not args.quiet:
        utils.print_operation_summary("Pip Analysis", total_pips, 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
