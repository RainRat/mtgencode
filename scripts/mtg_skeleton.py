#!/usr/bin/env python3
import sys
import os
import argparse
from collections import defaultdict

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import datalib
import cardlib

def main():
    parser = argparse.ArgumentParser(
        description="Generate a 'Design Skeleton' (Set Skeleton) for a card dataset, bucketing by type and CMC.",
        epilog='''
The Design Skeleton helps you understand the mechanical curve and balance of your set.
It displays a 2D grid of card types (Creature, Instant, etc.) vs. mana costs (CMC 0-7+).
'''
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (MTGJSON, Scryfall, CSV, XML, MSE, or encoded text). Defaults to stdin (-).')

    # Group: Data Processing
    proc_group = parser.add_argument_group('Data Processing')
    proc_group.add_argument('-n', '--limit', type=int, default=0,
                        help='Only process the first N cards.')
    proc_group.add_argument('--shuffle', action='store_true',
                        help='Randomize the order of cards before analyzing.')
    proc_group.add_argument('--sample', type=int, default=0,
                        help='Pick N random cards (shorthand for --shuffle --limit N).')
    proc_group.add_argument('--seed', type=int,
                        help='Seed for the random number generator.')

    # Group: Filtering Options
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

    # Determine if we should use color
    use_color = False
    if args.color is True:
        use_color = True
    elif args.color is None and sys.stdout.isatty():
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

    # Define types and CMC buckets
    tracked_types = ["Creature", "Instant", "Sorcery", "Enchantment", "Artifact", "Planeswalker", "Land", "Battle"]
    cmc_buckets = [0, 1, 2, 3, 4, 5, 6, 7] # 7 means 7+

    # Matrix: matrix[type][cmc] = count
    matrix = defaultdict(lambda: defaultdict(int))

    for card in cards:
        # Determine CMC bucket
        cmc = int(card.cost.cmc)
        if cmc > 7:
            cmc = 7
        elif cmc < 0:
            cmc = 0

        # A card can have multiple types, but we usually want to bucket it by primary
        # We'll check in order of priority or just add to all that match?
        # Standard design skeletons usually bucket by primary type.
        # Let's count it for every type it has that is in our tracked list.
        found_any = False
        for t in tracked_types:
            if card._has_type(t):
                matrix[t][cmc] += 1
                found_any = True

        if not found_any:
            matrix["Other"][cmc] += 1

    # Prepare table rows
    header = ["Type / CMC"] + [str(c) if c < 7 else "7+" for c in cmc_buckets] + ["Total"]
    if use_color:
        header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

    rows = [header]

    all_rows = tracked_types + (["Other"] if any(matrix["Other"].values()) else [])

    grand_total = 0
    column_totals = defaultdict(int)

    for t in all_rows:
        row_total = 0
        row_label = t
        if use_color:
            color = utils.Ansi.CYAN
            if t == "Creature": color = utils.Ansi.GREEN
            elif t == "Land": color = utils.Ansi.BOLD
            row_label = utils.colorize(t, color)

        row = [row_label]
        for cmc in cmc_buckets:
            count = matrix[t][cmc]
            row.append(datalib.color_count(count, use_color) if count > 0 else "-")
            row_total += count
            column_totals[cmc] += count

        row.append(utils.colorize(str(row_total), utils.Ansi.BOLD + utils.Ansi.YELLOW) if use_color else str(row_total))
        grand_total += row_total
        rows.append(row)

    # Add separators
    datalib.add_separator_row(rows, index=1)
    datalib.add_separator_row(rows, index=len(rows))

    # Add totals row
    totals_label = "TOTAL"
    if use_color:
        totals_label = utils.colorize(totals_label, utils.Ansi.BOLD + utils.Ansi.YELLOW)

    totals_row = [totals_label]
    for cmc in cmc_buckets:
        count = column_totals[cmc]
        totals_row.append(utils.colorize(str(count), utils.Ansi.BOLD + utils.Ansi.YELLOW) if use_color else str(count))

    totals_row.append(utils.colorize(str(grand_total), utils.Ansi.BOLD + utils.Ansi.WHITE + utils.Ansi.UNDERLINE) if use_color else str(grand_total))
    rows.append(totals_row)

    # Print
    print(utils.colorize("DESIGN SKELETON", utils.Ansi.BOLD + utils.Ansi.CYAN + utils.Ansi.UNDERLINE) if use_color else "=== DESIGN SKELETON ===")
    datalib.printrows(datalib.padrows(rows, aligns=['l'] + ['r'] * (len(header) - 1)), indent=2)

    if not args.quiet:
        utils.print_operation_summary("Skeleton Analysis", grand_total, 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
