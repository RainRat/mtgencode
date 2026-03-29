#!/usr/bin/env python3
import sys
import os
import argparse
from collections import Counter

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import datalib

# List of all mechanics recognized by lib/cardlib.py
RECOGNIZED_MECHANICS = [
    'Activated', 'Triggered', 'ETB Effect', 'Modal/Choice', 'X-Cost/Effect',
    'Kicker', 'Uncast', 'Equipment', 'Leveler', 'Counters',
    'Flying', 'Trample', 'Lifelink', 'Haste', 'Deathtouch', 'Vigilance',
    'Ward', 'Prowess', 'Menace', 'Reach', 'Flash', 'Indestructible',
    'Defender', 'Scry', 'Draw A Card', 'Mill', 'Exile', 'Token',
    'Discard', 'Cycling', 'Convoke'
]

def main():
    parser = argparse.ArgumentParser(description="List all recognized mechanical keywords and optionally count their frequency in a dataset.")

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default=None,
                        help='Input card data (MTGJSON, Scryfall, CSV, etc.) to count mechanics. If not provided, just lists recognized mechanics.')

    # Group: Data Processing
    proc_group = parser.add_argument_group('Data Processing')
    proc_group.add_argument('--sort', choices=['name', 'count'], default='name',
                        help='Sort mechanics by name or frequency count (Default: name).')
    proc_group.add_argument('--reverse', action='store_true', help='Reverse the sort order.')
    proc_group.add_argument('--limit', type=int, default=0, help='Only show the top N mechanics.')

    # Group: Filtering Options (Standard across tools)
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('--set', action='append', help='Only include cards from specific sets.')
    filter_group.add_argument('--rarity', action='append', help='Only include cards of specific rarities.')
    filter_group.add_argument('--grep', action='append', help='Only include cards matching a search pattern.')
    filter_group.add_argument('--colors', action='append', help='Only include cards of specific colors.')
    filter_group.add_argument('--cmc', action='append', help='Only include cards with specific CMC values.')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    debug_group.add_argument('-q', '--quiet', action='store_true', help='Suppress the progress bar.')

    # Color options
    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color output.')

    args = parser.parse_args()

    # Determine if we should use color
    use_color = False
    if args.color is True:
        use_color = True
    elif args.color is None and sys.stdout.isatty():
        use_color = True

    if not args.infile:
        # Just list recognized mechanics
        print(utils.colorize("RECOGNIZED MECHANICS", utils.Ansi.BOLD + utils.Ansi.CYAN + utils.Ansi.UNDERLINE) if use_color else "=== RECOGNIZED MECHANICS ===")
        for m in sorted(RECOGNIZED_MECHANICS):
            print(f"  - {utils.colorize(m, utils.Ansi.CYAN) if use_color else m}")
        print(f"\nTotal: {len(RECOGNIZED_MECHANICS)} mechanics.")
        return

    # Load cards and count mechanics
    cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose,
                                  sets=args.set, rarities=args.rarity,
                                  grep=args.grep, colors=args.colors, cmcs=args.cmc)

    if not cards:
        print("No cards found matching criteria.", file=sys.stderr)
        return

    counts = Counter()
    for card in cards:
        for m in card.mechanics:
            counts[m] += 1

    # Prepare data for display
    total_cards = len(cards)
    results = []
    for m in RECOGNIZED_MECHANICS:
        count = counts.get(m, 0)
        results.append({'name': m, 'count': count})

    # Add any other mechanics found (though get_face_mechanics only returns from our list)
    for m in counts:
        if m not in RECOGNIZED_MECHANICS:
            results.append({'name': m, 'count': counts[m]})

    # Sorting
    if args.sort == 'name':
        results.sort(key=lambda x: x['name'].lower(), reverse=args.reverse)
    else:
        results.sort(key=lambda x: x['count'], reverse=not args.reverse)

    if args.limit > 0:
        results = results[:args.limit]

    # Display results
    header = ["Mechanic", "Count", "Percent", "Frequency"]
    if use_color:
        header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

    rows = [header]
    for r in results:
        name = r['name']
        count = r['count']
        percent = (count / total_cards * 100) if total_cards > 0 else 0
        bar = datalib.get_bar_chart(percent, use_color, color=utils.Ansi.CYAN)

        name_str = utils.colorize(name, utils.Ansi.CYAN) if use_color else name
        count_str = datalib.color_count(count, use_color, utils.Ansi.BOLD + utils.Ansi.GREEN) if use_color else str(count)

        rows.append([name_str, count_str, f"{percent:5.1f}%", bar])

    # Get column widths and add a separator
    col_widths = datalib.get_col_widths(rows)
    separator = ['-' * w for w in col_widths]
    rows.insert(1, separator)

    print(utils.colorize(f"MECHANICAL FREQUENCY (Total Cards: {total_cards})", utils.Ansi.BOLD + utils.Ansi.CYAN + utils.Ansi.UNDERLINE) if use_color else f"=== MECHANICAL FREQUENCY (Total Cards: {total_cards}) ===")
    datalib.printrows(datalib.padrows(rows, aligns=['l', 'r', 'r', 'l']), indent=2)

    # Provide clear feedback on operation completion
    utils.print_operation_summary("Analysis", total_cards, 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
