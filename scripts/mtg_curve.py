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

def main():
    parser = argparse.ArgumentParser(
        description="Analyze and visualize the mana curve (CMC distribution) of a card dataset or decklist.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
The Mana Curve is a fundamental metric for deckbuilding and set design.
This tool provides a focused visualization of how cards are distributed across different mana costs.

Usage Examples:
  # Analyze the curve of a specific set
  python3 scripts/mtg_curve.py data/AllPrintings.json --set MOM

  # Analyze a decklist file
  python3 scripts/mtg_curve.py my_deck.txt

  # See the curve for only creatures in a dataset
  python3 scripts/mtg_curve.py data/AllPrintings.json --grep-type "Creature"
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (MTGJSON, Scryfall, CSV, XML, MSE, or encoded text) or decklist. Defaults to stdin (-).')

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
                                  shuffle=args.shuffle, seed=args.seed)

    if args.limit > 0:
        cards = cards[:args.limit]

    if not cards:
        if not args.quiet:
            print("No cards found matching the criteria.", file=sys.stderr)
        return

    # Analysis Data Structures
    cmc_buckets = [0, 1, 2, 3, 4, 5, 6, 7] # 7 means 7+
    cmc_counts = defaultdict(int)
    type_counts = defaultdict(lambda: defaultdict(int)) # type -> cmc -> count
    color_sums = defaultdict(float) # color -> sum of CMC
    color_counts = defaultdict(int) # color -> count of cards

    total_cmc = 0
    total_cards = len(cards)

    for card in cards:
        # Determine CMC bucket
        cmc = int(card.cost.cmc)
        total_cmc += card.cost.cmc
        bucket = cmc if cmc < 7 else 7
        if bucket < 0: bucket = 0

        cmc_counts[bucket] += 1

        # Type Breakdown (Creature vs Non-creature)
        is_creature = card.is_creature
        type_key = "Creature" if is_creature else "Non-creature"
        type_counts[type_key][bucket] += 1

        # Color Analysis
        card_colors = card.cost.colors
        if not card_colors:
            card_colors = ['C'] # Colorless

        for color in card_colors:
            color_sums[color] += card.cost.cmc
            color_counts[color] += 1

    # 1. Global Header
    utils.print_header("MANA CURVE ANALYSIS", count=total_cards, use_color=use_color)

    avg_cmc = total_cmc / total_cards
    avg_str = f"Global Average CMC: {avg_cmc:.2f}"
    if use_color:
        avg_str = utils.colorize(avg_str, utils.Ansi.BOLD + utils.Ansi.GREEN)
    print(f"  {avg_str}\n")

    # 2. Distribution Chart
    print(f"  {datalib.color_line('CMC Distribution Chart:', use_color)}")

    header = ["CMC", "Count", "Percent", "Distribution (Creature / Non-creature)"]
    if use_color:
        header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

    rows = [header]
    for bucket in cmc_buckets:
        count = cmc_counts[bucket]
        percent = (count / total_cards * 100)

        label = str(bucket) if bucket < 7 else "7+"
        if use_color:
            label = utils.colorize(label, utils.Ansi.CYAN)

        # Composite bar chart
        bar_width = 20
        c_count = type_counts["Creature"][bucket]
        nc_count = type_counts["Non-creature"][bucket]

        if count > 0:
            # Determine total bar length based on the bucket with the most cards
            max_bucket_count = max(cmc_counts.values())
            total_bar_len = int(round(count / max_bucket_count * bar_width))
            if total_bar_len == 0: total_bar_len = 1

            # Divide that length between creatures and non-creatures
            if count > 0:
                c_width = int(round(c_count / count * total_bar_len))
                nc_width = total_bar_len - c_width

                # Ensure at least one block for each type if it exists in the bucket
                if c_count > 0 and c_width == 0:
                    c_width = 1
                    if nc_width > 0: nc_width -= 1
                if nc_count > 0 and nc_width == 0:
                    nc_width = 1
                    if c_width > 0: c_width -= 1
            else:
                c_width = nc_width = 0

            if use_color:
                c_bar = utils.colorize('█' * c_width, utils.Ansi.GREEN)
                nc_bar = utils.colorize('▓' * nc_width, utils.Ansi.YELLOW)
                bar = '[' + c_bar + nc_bar + ' ' * (bar_width - (c_width + nc_width)) + ']'
            else:
                bar = '[' + '#' * c_width + '=' * nc_width + ' ' * (bar_width - (c_width + nc_width)) + ']'
        else:
            bar = '[' + ' ' * bar_width + ']'

        rows.append([
            label,
            datalib.color_count(count, use_color),
            f"{percent:5.1f}%",
            bar
        ])

    datalib.add_separator_row(rows)
    datalib.printrows(datalib.padrows(rows, aligns=['r', 'r', 'r', 'l']), indent=4)
    print()

    # Legend for the chart
    if use_color:
        c_legend = utils.colorize("█ Creature", utils.Ansi.GREEN)
        nc_legend = utils.colorize("▓ Non-creature", utils.Ansi.YELLOW)
        print(f"    Legend: {c_legend}  {nc_legend}\n")
    else:
        print("    Legend: # Creature  = Non-creature\n")

    # 3. Average CMC by Color
    print(f"  {datalib.color_line('Average CMC by Color:', use_color)}")

    color_header = ["Color", "Avg CMC", "Count", "Percentage"]
    if use_color:
        color_header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in color_header]

    c_rows = [color_header]
    # WUBRGC sort order
    for color in ['W', 'U', 'B', 'R', 'G', 'C']:
        count = color_counts[color]
        if count == 0: continue

        avg = color_sums[color] / count
        percent = (count / total_cards * 100)

        label = color
        if use_color:
            label = utils.colorize(color, utils.Ansi.get_color_color(color))

        c_rows.append([
            label,
            f"{avg:.2f}",
            datalib.color_count(count, use_color),
            f"{percent:5.1f}%"
        ])

    if len(c_rows) > 1:
        datalib.add_separator_row(c_rows)
        datalib.printrows(datalib.padrows(c_rows, aligns=['l', 'r', 'r', 'r']), indent=4)
        print()

    if not args.quiet:
        utils.print_operation_summary("Curve Analysis", total_cards, 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
