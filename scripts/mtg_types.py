#!/usr/bin/env python3
import sys
import os
import argparse
import json
import csv
from collections import Counter, defaultdict

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import datalib
import cardlib

TRACKED_TYPES = ["Creature", "Instant", "Sorcery", "Enchantment", "Artifact", "Planeswalker", "Land", "Battle"]
COLOR_GROUPS = 'WUBRGAM'

def get_color_group(card):
    """Categorizes a card into one of the color pie groups: W, U, B, R, G, A (Colorless), M (Multicolored)."""
    identity = card.color_identity
    if len(identity) > 1:
        return 'M'
    if len(identity) == 1:
        return identity[0]
    return 'A'

def analyze_dataset(path, args):
    """Loads a dataset and returns (matrix, row_totals, col_totals, cards_processed)."""
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
                                  decklist_file=args.deck,
                                  shuffle=args.shuffle, seed=args.seed,
                                  booster=args.booster, box=args.box)

    if args.limit > 0:
        cards = cards[:args.limit]

    if not cards:
        return None, None, None, 0

    # matrix[type][color] = count
    matrix = defaultdict(Counter)
    row_totals = Counter()
    col_totals = Counter()

    for card in cards:
        color = get_color_group(card)
        col_totals[color] += 1

        found_any = False
        for t in TRACKED_TYPES:
            if card._has_type(t):
                matrix[t][color] += 1
                row_totals[t] += 1
                found_any = True

        if not found_any:
            matrix["Other"][color] += 1
            row_totals["Other"] += 1

    return matrix, row_totals, col_totals, len(cards)

def main():
    parser = argparse.ArgumentParser(
        description="Generate a Type vs. Color heatmap cross-referencing card types with Color Identity.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool provides a 2D grid showing how card types (Creature, Instant, etc.) are distributed
across the five colors of Magic, as well as Colorless (A) and Multicolored (M) cards.
This is essential for verifying color-pie balance and archetypal distribution in a set.

Usage Examples:
  # Analyze the type/color distribution of a specific set
  python3 scripts/mtg_types.py data/AllPrintings.json --set MOM

  # Compare type/color distribution between official data and AI designs
  python3 scripts/mtg_types.py data/AllPrintings.json --compare generated.txt

  # View distribution for only rare cards as JSON
  python3 scripts/mtg_types.py data/AllPrintings.json --rarity rare --json
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, XML, or encoded text). '
                             'Defaults to stdin (-). If data/AllPrintings.json exists, it is used '
                             'automatically when run interactively.')
    io_group.add_argument('query', nargs='?', default=None,
                        help='Optional search query. If provided, it is added to --grep.')
    io_group.add_argument('--compare', '-c',
                        help='Optional second dataset to compare against the primary input.')

    # Group: Output Format
    fmt_group_title = parser.add_argument_group('Output Format')
    fmt_group = fmt_group_title.add_mutually_exclusive_group()
    fmt_group.add_argument('--table', action='store_true', help='Generate a formatted table (Default for terminal).')
    fmt_group.add_argument('--json', action='store_true', help='Generate a JSON file.')
    fmt_group.add_argument('--csv', action='store_true', help='Generate a CSV file.')

    # Group: Content Formatting
    enc_group = parser.add_argument_group('Content Formatting')
    enc_group.add_argument('--nolabel', action='store_true',
                        help="Input file does not have field labels (like '|cost|' or '|text|').")
    enc_group.add_argument('--nolinetrans', action='store_true',
                        help='Input file does not use automatic line reordering.')

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
                        help='Skip cards matching a search pattern. Use multiple times for OR logic.')
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
                        help="Only include cards of specific rarities. Supports full names or shorthands: O (Common), N (Uncommon), A (Rare), Y (Mythic), I (Special), L (Basic Land).")
    filter_group.add_argument('--colors', action='append',
                        help="Only include cards of specific colors (W, U, B, R, G, C, A).")
    filter_group.add_argument('--identity', action='append',
                        help="Only include cards with specific color identities.")
    filter_group.add_argument('--id-count', action='append',
                        help='Only include cards with specific color identity counts.')
    filter_group.add_argument('--cmc', action='append',
                        help='Only include cards with specific CMC values.')
    filter_group.add_argument('--pow', '--power', action='append', dest='pow',
                        help='Only include cards with specific Power values.')
    filter_group.add_argument('--tou', '--toughness', action='append', dest='tou',
                        help='Only include cards with specific Toughness values.')
    filter_group.add_argument('--loy', '--loyalty', '--defense', action='append', dest='loy',
                        help='Only include cards with specific Loyalty or Defense values.')
    filter_group.add_argument('--mechanic', action='append',
                        help='Only include cards with specific mechanical features.')
    filter_group.add_argument('--deck-filter', '--decklist-filter', dest='deck',
                        help='Filter cards using a standard MTG decklist file.')

    # Group: Browsing Options
    browsing_group = parser.add_argument_group('Browsing Options')
    browsing_group.add_argument('-n', '--limit', type=int, default=0,
                        help='Only process the first N cards.')
    browsing_group.add_argument('--shuffle', action='store_true',
                        help='Shuffle the cards before processing.')
    browsing_group.add_argument('--sample', type=int, default=0,
                        help='Pick N random cards (shorthand for --shuffle --limit N).')
    browsing_group.add_argument('--seed', type=int,
                        help='Seed for the random number generator.')
    browsing_group.add_argument('--booster', type=int, default=0,
                        help='Simulate opening N booster packs.')
    browsing_group.add_argument('--box', type=int, default=0,
                        help='Simulate opening N booster boxes (36 packs each).')

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
    if args.infile and args.infile != '-' and not args.query:
        if not os.path.exists(args.infile):
            args.query = args.infile
            args.infile = '-'

    if args.query:
        if not args.grep: args.grep = []
        args.grep.append(args.query)

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

    if args.sample > 0:
        args.shuffle = True
        args.limit = args.sample

    # Determine if we should use color
    use_color = False
    if args.color is True:
        use_color = True
    elif args.color is None and not (args.json or args.csv) and sys.stdout.isatty():
        use_color = True

    # Analysis
    matrix1, row_totals1, col_totals1, total_cards1 = analyze_dataset(args.infile, args)
    if not matrix1:
        if not args.quiet:
            print("No cards found in primary dataset matching criteria.", file=sys.stderr)
        return

    matrix2, row_totals2, col_totals2, total_cards2 = None, None, None, 0
    if args.compare:
        matrix2, row_totals2, col_totals2, total_cards2 = analyze_dataset(args.compare, args)
        if not matrix2:
            if not args.quiet:
                print(f"No cards found in comparison dataset: {args.compare}", file=sys.stderr)

    all_rows = TRACKED_TYPES + (["Other"] if row_totals1["Other"] > 0 or (row_totals2 and row_totals2["Other"] > 0) else [])
    groups = COLOR_GROUPS

    if args.json:
        results = {
            'primary': {
                'total': total_cards1,
                'col_totals': dict(col_totals1),
                'row_totals': dict(row_totals1),
                'matrix': {t: dict(matrix1[t]) for t in all_rows}
            }
        }
        if matrix2:
            results['comparison'] = {
                'total': total_cards2,
                'col_totals': dict(col_totals2),
                'row_totals': dict(row_totals2),
                'matrix': {t: dict(matrix2[t]) for t in all_rows}
            }
        print(json.dumps(results, indent=2))

    elif args.csv:
        writer = csv.writer(sys.stdout)
        if matrix2:
            writer.writerow(['Type', 'Color', 'Primary Count', 'Comp Count', 'Delta'])
            for t in all_rows:
                for g in groups:
                    c1 = matrix1[t][g]
                    c2 = matrix2[t][g]
                    writer.writerow([t, g, c1, c2, c2 - c1])
        else:
            writer.writerow(['Type'] + list(groups) + ['Total'])
            for t in all_rows:
                row = [t] + [matrix1[t][g] for g in groups] + [row_totals1[t]]
                writer.writerow(row)
            writer.writerow(['TOTAL'] + [col_totals1[g] for g in groups] + [total_cards1])

    else:
        # Table output
        title = "TYPE / COLOR DISTRIBUTION"
        if matrix2:
            title += " (COMPARISON)"

        utils.print_header(title, count=total_cards1, use_color=use_color)
        if matrix2:
            print(f"  Comparison Dataset: {args.compare} ({total_cards2} cards)\n")

        header = ["Type / Color"] + [g for g in groups] + ["Total"]
        if use_color:
            header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

        rows = [header]
        for t in all_rows:
            row_label = t
            if use_color:
                color = utils.Ansi.CYAN
                if t == "Creature": color = utils.Ansi.GREEN
                elif t == "Land": color = utils.Ansi.BOLD
                row_label = utils.colorize(t, color)

            row = [row_label]
            for g in groups:
                c1 = matrix1[t][g]
                if matrix2:
                    c2 = matrix2[t][g]
                    delta = c2 - c1
                    val_str = str(c2)
                    if delta == 0:
                        display_val = " - " if c2 == 0 else val_str
                    else:
                        color = utils.Ansi.GREEN if delta > 0 else utils.Ansi.RED
                        indicator = "▲" if delta > 0 else "▼"
                        if use_color:
                            display_val = utils.colorize(f"{val_str}{indicator}", color)
                        else:
                            display_val = f"{val_str}{indicator}"
                else:
                    display_val = datalib.color_count(c1, use_color) if c1 > 0 else " - "
                row.append(display_val)

            # Row Total
            r_total = row_totals1[t]
            if matrix2:
                r_total2 = row_totals2[t]
                delta = r_total2 - r_total
                val_str = str(r_total2)
                if delta == 0:
                    display_total = val_str
                else:
                    color = utils.Ansi.GREEN if delta > 0 else utils.Ansi.RED
                    indicator = "▲" if delta > 0 else "▼"
                    if use_color:
                        display_total = utils.colorize(f"{val_str}{indicator}", color + utils.Ansi.BOLD)
                    else:
                        display_total = f"{val_str}{indicator}"
            else:
                display_total = utils.colorize(str(r_total), utils.Ansi.BOLD + utils.Ansi.YELLOW) if use_color else str(r_total)

            row.append(display_total)
            rows.append(row)

        datalib.add_separator_row(rows)

        # Totals Row
        totals_label = "TOTAL"
        if use_color:
            totals_label = utils.colorize(totals_label, utils.Ansi.BOLD + utils.Ansi.YELLOW)

        totals_row = [totals_label]
        for g in groups:
            c_total = col_totals1[g]
            if matrix2:
                c_total2 = col_totals2[g]
                delta = c_total2 - c_total
                val_str = str(c_total2)
                if delta == 0:
                    display_c_total = val_str
                else:
                    color = utils.Ansi.GREEN if delta > 0 else utils.Ansi.RED
                    indicator = "▲" if delta > 0 else "▼"
                    if use_color:
                        display_c_total = utils.colorize(f"{val_str}{indicator}", color + utils.Ansi.BOLD)
                    else:
                        display_c_total = f"{val_str}{indicator}"
            else:
                display_c_total = utils.colorize(str(c_total), utils.Ansi.BOLD + utils.Ansi.YELLOW) if use_color else str(c_total)
            totals_row.append(display_c_total)

        grand_total = total_cards1
        if matrix2:
            grand_total2 = total_cards2
            delta = grand_total2 - grand_total
            val_str = str(grand_total2)
            if delta == 0:
                display_grand = val_str
            else:
                color = utils.Ansi.GREEN if delta > 0 else utils.Ansi.RED
                indicator = "▲" if delta > 0 else "▼"
                if use_color:
                    display_grand = utils.colorize(f"{val_str}{indicator}", color + utils.Ansi.BOLD + utils.Ansi.UNDERLINE)
                else:
                    display_grand = f"{val_str}{indicator}"
        else:
            display_grand = utils.colorize(str(grand_total), utils.Ansi.BOLD + utils.Ansi.WHITE + utils.Ansi.UNDERLINE) if use_color else str(grand_total)

        totals_row.append(display_grand)
        rows.append(totals_row)

        datalib.printrows(datalib.padrows(rows, aligns=['l'] + ['r']*(len(groups)+1)), indent=2)

    if not args.quiet:
        utils.print_operation_summary("Type Analysis", total_cards1 + total_cards2, 0)

if __name__ == "__main__":
    main()
