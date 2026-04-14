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

def count_pips(cards, include_text=False):
    """Aggregates mana symbol counts from a list of cards."""
    counts = {
        'W': 0, 'U': 0, 'B': 0, 'R': 0, 'G': 0,
        'C': 0, 'S': 0, 'X': 0, 'P': 0
    }

    def process_face(card):
        # Casting cost pips
        for sym, count in card.cost.symbols.items():
            for char in sym:
                if char in counts:
                    counts[char] += count

        # Rules text pips
        if include_text:
            for cost in card.text.costs:
                for sym, count in cost.symbols.items():
                    for char in sym:
                        if char in counts:
                            counts[char] += count

        if card.bside:
            process_face(card.bside)

    for card in cards:
        process_face(card)

    return counts

def main():
    parser = argparse.ArgumentParser(
        description="Analyze mana symbol (pip) distribution in a card dataset.",
        epilog='''
Usage Examples:
  # Analyze pips for a specific set
  python3 scripts/mtg_pips.py data/AllPrintings.json --set MOM

  # Include pips found in rules text (activated abilities, etc.)
  python3 scripts/mtg_pips.py data/AllPrintings.json --include-text

  # Export pip distribution to a JSON file
  python3 scripts/mtg_pips.py data/AllPrintings.json --json pips.json
''' ,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, XML, MSE, JSONL, ZIP, or Decklist), encoded text, or directory. Defaults to stdin (-).')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save the analysis results. If not provided, results print to the console.')
    io_group.add_argument('--include-text', action='store_true',
                        help='Include mana symbols found in rules text (e.g. activated abilities).')

    # Group: Output Format (Mutually Exclusive)
    fmt_group_title = parser.add_argument_group('Output Format')
    fmt_group = fmt_group_title.add_mutually_exclusive_group()
    fmt_group.add_argument('--table', action='store_true',
                           help='Generate a formatted table for terminal view (Default).')
    fmt_group.add_argument('--json', action='store_true',
                           help='Generate a structured JSON file.')
    fmt_group.add_argument('--csv', action='store_true',
                           help='Generate a CSV file.')

    # Group: Processing Options
    proc_group = parser.add_argument_group('Processing Options')
    proc_group.add_argument('-n', '--limit', type=int, default=0,
                        help='Only process the first N cards.')
    proc_group.add_argument('--shuffle', action='store_true',
                        help='Shuffle the cards before processing.')
    proc_group.add_argument('--sample', type=int, default=0,
                        help='Pick N random cards (shorthand for --shuffle --limit N).')

    # Group: Filtering Options (Standard across tools)
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('-g', '--grep', action='append',
                        help='Only include cards matching a search pattern.')
    filter_group.add_argument('--vgrep', '--exclude', action='append',
                        help='Skip cards matching a search pattern.')
    filter_group.add_argument('--set', action='append',
                        help='Only include cards from specific sets.')
    filter_group.add_argument('--rarity', action='append',
                        help="Only include cards of specific rarities.")
    filter_group.add_argument('--colors', action='append',
                        help="Only include cards of specific colors.")
    filter_group.add_argument('--cmc', action='append',
                        help='Only include cards with specific CMC values.')
    filter_group.add_argument('--pow', '--power', action='append', dest='pow',
                        help='Only include cards with specific Power values.')
    filter_group.add_argument('--tou', '--toughness', action='append', dest='tou',
                        help='Only include cards with specific Toughness values.')
    filter_group.add_argument('--loy', '--loyalty', '--defense', action='append', dest='loy',
                        help='Only include cards with specific Loyalty or Defense values.')
    filter_group.add_argument('--mechanic', action='append',
                        help='Only include cards with specific mechanics.')
    filter_group.add_argument('--deck-filter', '--decklist-filter', dest='deck',
                        help='Filter cards using a standard MTG decklist file.')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    debug_group.add_argument('-q', '--quiet', action='store_true', help='Suppress status messages.')

    # Color options
    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None,
                        help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color',
                        help='Disable ANSI color output.')

    args = parser.parse_args()

    # Handle --sample
    if args.sample > 0:
        args.shuffle = True
        args.limit = args.sample

    # Load and filter cards
    cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose,
                                  grep=args.grep, vgrep=args.vgrep,
                                  sets=args.set, rarities=args.rarity,
                                  colors=args.colors, cmcs=args.cmc,
                                  pows=args.pow, tous=args.tou, loys=args.loy,
                                  mechanics=args.mechanic,
                                  decklist_file=args.deck,
                                  shuffle=args.shuffle)

    if args.limit > 0:
        cards = cards[:args.limit]

    total_cards = len(cards)
    if total_cards == 0 and not args.quiet:
        print("No cards found matching the criteria.", file=sys.stderr)
        return

    # Count pips
    counts = count_pips(cards, include_text=args.include_text)
    total_pips = sum(counts.values())

    # Determine if we should use color
    use_color = False
    if args.color is True:
        use_color = True
    elif args.color is None and not (args.json or args.csv) and sys.stdout.isatty():
        use_color = True

    # Set default format if none chosen
    if not (args.json or args.csv or args.table):
        if args.outfile:
            if args.outfile.endswith('.json'): args.json = True
            elif args.outfile.endswith('.csv'): args.csv = True
            else: args.table = True
        else:
            args.table = True

    # Output processing
    output_f = sys.stdout
    if args.outfile:
        output_f = open(args.outfile, 'w', encoding='utf-8')

    try:
        if args.json:
            json.dump({'total_cards': total_cards, 'total_pips': total_pips, 'counts': counts}, output_f, indent=2)
        elif args.csv:
            writer = csv.writer(output_f)
            writer.writerow(['Symbol', 'Count', 'Percent'])
            for sym in sorted(counts.keys()):
                percent = (counts[sym] / total_pips * 100) if total_pips > 0 else 0
                writer.writerow([sym, counts[sym], f"{percent:.1f}%"])
        else: # Table
            header_title = "MANA PIP ANALYSIS"
            match_count = f" ({total_cards} cards processed)"
            header_text = header_title + match_count

            if use_color:
                header_main = utils.colorize(header_title, utils.Ansi.BOLD + utils.Ansi.CYAN)
                header_count = utils.colorize(match_count, utils.Ansi.CYAN)
                output_f.write("  " + header_main + header_count + '\n')
            else:
                output_f.write("  " + header_text + '\n')

            output_f.write("  " + "=" * len(header_text) + '\n')

            header = ["Symbol", "Count", "Percent", "Distribution"]
            if use_color:
                header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

            rows = [header]
            for sym in 'WUBRGCSPX':
                if sym not in counts: continue
                count = counts[sym]
                percent = (count / total_pips * 100) if total_pips > 0 else 0

                display_sym = sym
                if use_color:
                    color = utils.Ansi.get_color_color(sym)
                    display_sym = utils.colorize(sym, color)

                bar = datalib.get_bar_chart(percent, use_color, color=utils.Ansi.get_color_color(sym) if use_color else None)

                rows.append([
                    display_sym,
                    str(count),
                    f"{percent:5.1f}%",
                    bar
                ])

            datalib.add_separator_row(rows)
            for row in datalib.padrows(rows, aligns=['l', 'r', 'r', 'l']):
                output_f.write("  " + row + '\n')

            footer = f"\n  Total Pips: {total_pips}"
            if use_color:
                footer = utils.colorize(footer, utils.Ansi.BOLD + utils.Ansi.GREEN)
            output_f.write(footer + '\n')

    finally:
        if args.outfile:
            output_f.close()

    if not args.quiet:
        utils.print_operation_summary("Analysis", total_cards, 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
