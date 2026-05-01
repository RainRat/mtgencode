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
import cardlib
from cardlib import RECOGNIZED_MECHANICS

def main():
    parser = argparse.ArgumentParser(
        description="List all recognized mechanical keywords and optionally count their frequency in a dataset.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool identifies mechanical features and keyword abilities (like Flying, Kicker, or ETB Effect) in card text. It can be used to see which mechanics the toolkit tracks or to analyze the mechanical profile of a dataset.

Usage Examples:
  # List all mechanics recognized by the toolkit
  python3 scripts/mtg_mechanics.py

  # Count the frequency of mechanics in a specific set
  python3 scripts/mtg_mechanics.py data/AllPrintings.json --set MOM

  # Compare mechanics between official data and AI-generated cards
  python3 scripts/mtg_mechanics.py data/AllPrintings.json --compare generated.txt

  # Find the most common mechanics in a custom card pool
  python3 scripts/mtg_mechanics.py my_cards.json --sort count --reverse --limit 10

  # Count mechanics for only rare creatures
  python3 scripts/mtg_mechanics.py data/AllPrintings.json --rarity rare --grep "Creature"
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default=None,
                        help='Input card data (MTGJSON, Scryfall, CSV, XML, or encoded text) to analyze. If not provided, it defaults to data/AllPrintings.json if available, or just lists all recognized mechanics. Supports standard input (-).')
    io_group.add_argument('--compare', '-c',
                        help='Optional second dataset to compare against the primary input. Displays a side-by-side frequency comparison with delta indicators.')

    # Group: Content Formatting
    enc_group = parser.add_argument_group('Content Formatting')
    enc_group.add_argument('--nolabel', action='store_true',
                        help="Input file does not have field labels (like '|cost|' or '|text|').")
    enc_group.add_argument('--nolinetrans', action='store_true',
                        help='Input file does not use automatic line reordering.')

    # Group: Data Processing
    proc_group = parser.add_argument_group('Data Processing')
    proc_group.add_argument('--sort', choices=['name', 'count'], default='name',
                        help='Sort mechanics by name or frequency (Default: name).')
    proc_group.add_argument('--reverse', action='store_true', help='Reverse the sort order.')
    proc_group.add_argument('-n', '--max-cards', type=int, default=0, help='Only process the first N cards from each input.')
    proc_group.add_argument('-t', '--top', '--limit', dest='top', type=int, default=0, help='Only show the top N mechanics in the results.')

    # Group: Filtering Options (Standard across tools)
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('--grep', action='append',
                        help='Only include cards matching a search pattern (checks name, typeline, rules text, cost, and stats). Use multiple times for AND logic.')
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
                        help='Simulate opening N booster packs.')
    filter_group.add_argument('--box', type=int, default=0,
                        help='Simulate opening N booster boxes (36 packs each).')
    filter_group.add_argument('--shuffle', action='store_true',
                        help='Randomize the order of cards.')
    filter_group.add_argument('--sample', type=int, default=0,
                        help='Pick N random cards.')
    filter_group.add_argument('--seed', type=int,
                        help='Seed for the random number generator.')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    debug_group.add_argument('-q', '--quiet', action='store_true', help='Suppress the progress bar.')

    # Color options
    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color output.')

    args = parser.parse_args()

    # UX Improvement: Default Dataset
    # If we are reading from stdin but it's an interactive terminal, use AllPrintings.json if it exists.
    if (args.infile == '-' or args.infile is None) and sys.stdin.isatty():
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

    # Handle --sample
    if args.sample > 0:
        args.shuffle = True
        args.max_cards = args.sample

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
    def load_and_count(path):
        if not path:
            return None, None

        cards = jdecode.mtg_open_file(path, verbose=args.verbose,
                                      linetrans=not args.nolinetrans,
                                      fmt_labeled=None if args.nolabel else cardlib.fmt_labeled_default,
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
                                      decklist_file=args.deck, booster=args.booster, box=args.box,
                                      shuffle=args.shuffle, seed=args.seed)
        if args.max_cards > 0:
            cards = cards[:args.max_cards]

        if not cards:
            return None, 0

        counts = Counter()
        for card in cards:
            for m in card.mechanics:
                counts[m] += 1
        return counts, len(cards)

    counts1, total1 = load_and_count(args.infile)
    if not counts1:
        print(f"No cards found in {args.infile} matching criteria.", file=sys.stderr)
        return

    counts2, total2 = load_and_count(args.compare)

    # Prepare data for display
    all_mechanics = set(counts1.keys())
    if counts2:
        all_mechanics.update(counts2.keys())

    # We prioritize recognized mechanics then others
    ordered_mechanics = [m for m in RECOGNIZED_MECHANICS if m in all_mechanics]
    ordered_mechanics += sorted([m for m in all_mechanics if m not in RECOGNIZED_MECHANICS])

    results = []
    for m in ordered_mechanics:
        c1 = counts1.get(m, 0)
        p1 = (c1 / total1 * 100) if total1 > 0 else 0

        res = {'name': m, 'count1': c1, 'percent1': p1}

        if counts2:
            c2 = counts2.get(m, 0)
            p2 = (c2 / total2 * 100) if total2 > 0 else 0
            res.update({'count2': c2, 'percent2': p2, 'delta': p2 - p1})

        results.append(res)

    # Sorting
    if args.sort == 'name':
        results.sort(key=lambda x: x['name'].lower(), reverse=args.reverse)
    elif args.sort == 'count':
        # Default to base dataset count for sorting
        results.sort(key=lambda x: x['count1'], reverse=not args.reverse)

    if args.top > 0:
        results = results[:args.top]

    # Display results
    if counts2:
        header = ["Mechanic", f"% {os.path.basename(args.infile)[:15]}", f"% {os.path.basename(args.compare)[:15]}", "Delta", "Indicator"]
        if use_color:
            header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

        rows = [header]
        for r in results:
            name_str = utils.colorize(r['name'], utils.Ansi.CYAN) if use_color else r['name']
            p1_str = f"{r['percent1']:5.1f}%"
            p2_str = f"{r['percent2']:5.1f}%"

            delta = r['delta']
            delta_str = f"{delta:+6.1f}%"
            indicator = ""
            if delta > 0.1:
                indicator = "▲"
                if use_color:
                    delta_str = utils.colorize(delta_str, utils.Ansi.BOLD + utils.Ansi.GREEN)
                    indicator = utils.colorize(indicator, utils.Ansi.BOLD + utils.Ansi.GREEN)
            elif delta < -0.1:
                indicator = "▼"
                if use_color:
                    delta_str = utils.colorize(delta_str, utils.Ansi.BOLD + utils.Ansi.RED)
                    indicator = utils.colorize(indicator, utils.Ansi.BOLD + utils.Ansi.RED)
            else:
                indicator = "•"

            rows.append([name_str, p1_str, p2_str, delta_str, indicator])

        title = f"MECHANICAL COMPARISON ({total1} vs {total2} cards)"
        aligns = ['l', 'r', 'r', 'r', 'c']
    else:
        header = ["Mechanic", "Count", "Percent", "Frequency"]
        if use_color:
            header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

        rows = [header]
        for r in results:
            name = r['name']
            count = r['count1']
            percent = r['percent1']
            bar = datalib.get_bar_chart(percent, use_color, color=utils.Ansi.CYAN)

            name_str = utils.colorize(name, utils.Ansi.CYAN) if use_color else name
            count_str = datalib.color_count(count, use_color, utils.Ansi.BOLD + utils.Ansi.GREEN) if use_color else str(count)

            rows.append([name_str, count_str, f"{percent:5.1f}%", bar])

        title = f"MECHANICAL FREQUENCY (Total Cards: {total1})"
        aligns = ['l', 'r', 'r', 'l']

    # Get column widths and add a separator
    datalib.add_separator_row(rows)

    print(utils.colorize(title, utils.Ansi.BOLD + utils.Ansi.CYAN + utils.Ansi.UNDERLINE) if use_color else f"=== {title} ===")
    datalib.printrows(datalib.padrows(rows, aligns=aligns), indent=2)

    # Provide clear feedback on operation completion
    utils.print_operation_summary("Analysis", total1 + (total2 if total2 else 0), 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
