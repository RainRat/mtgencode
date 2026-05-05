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
from cardlib import RECOGNIZED_MECHANICS

def get_color_group(card):
    """Categorizes a card into one of the color pie groups: W, U, B, R, G, A (Colorless), M (Multicolored)."""
    identity = card.color_identity
    if len(identity) > 1:
        return 'M'
    if len(identity) == 1:
        return identity[0]
    return 'A'

def analyze_dataset(path, args):
    """Loads a dataset and returns (counts, totals, cards_processed)."""
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
        return None, None, 0

    # group_totals: group -> count of cards in that group
    # group_mechanics: group -> mechanic -> count of cards with that mechanic
    group_totals = Counter()
    group_mechanics = defaultdict(Counter)

    for card in cards:
        group = get_color_group(card)
        group_totals[group] += 1
        for m in card.mechanics:
            group_mechanics[group][m] += 1

    return group_mechanics, group_totals, len(cards)

def main():
    parser = argparse.ArgumentParser(
        description="Generate a Mechanical Color Pie heatmap cross-referencing mechanics with Color Identity.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool analyzes how mechanical keywords (like Flying, Trample, or Ward) are distributed across
the five colors of Magic, as well as Colorless and Multicolored cards. This is essential for
verifying color-pie integrity in a set design.

Usage Examples:
  # Analyze the color pie of a specific set
  python3 scripts/mtg_colorpie.py data/AllPrintings.json --set MOM

  # Compare the color pie of official data vs AI-generated cards
  python3 scripts/mtg_colorpie.py data/AllPrintings.json --compare generated.txt

  # View the color pie for only rare cards as JSON
  python3 scripts/mtg_colorpie.py data/AllPrintings.json --rarity rare --json
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
    group_mechanics, group_totals, total_cards = analyze_dataset(args.infile, args)
    if not group_mechanics:
        if not args.quiet:
            print("No cards found in primary dataset matching criteria.", file=sys.stderr)
        return

    comp_mechanics = None
    comp_totals = None
    total_comp = 0
    if args.compare:
        comp_mechanics, comp_totals, total_comp = analyze_dataset(args.compare, args)
        if not comp_mechanics:
            if not args.quiet:
                print(f"No cards found in comparison dataset: {args.compare}", file=sys.stderr)

    # Results preparation
    all_found_mechanics = set()
    for g in group_mechanics:
        all_found_mechanics.update(group_mechanics[g].keys())
    if comp_mechanics:
        for g in comp_mechanics:
            all_found_mechanics.update(comp_mechanics[g].keys())

    # Sort mechanics: Recognized ones first, then others
    ordered_mechanics = [m for m in RECOGNIZED_MECHANICS if m in all_found_mechanics]
    ordered_mechanics += sorted([m for m in all_found_mechanics if m not in RECOGNIZED_MECHANICS])

    groups = 'WUBRGAM'

    if args.json:
        results = {
            'primary': {
                'total': total_cards,
                'groups': dict(group_totals),
                'mechanics': {g: dict(group_mechanics[g]) for g in groups}
            }
        }
        if comp_mechanics:
            results['comparison'] = {
                'total': total_comp,
                'groups': dict(comp_totals),
                'mechanics': {g: dict(comp_mechanics[g]) for g in groups}
            }
        print(json.dumps(results, indent=2))

    elif args.csv:
        writer = csv.writer(sys.stdout)
        if comp_mechanics:
            writer.writerow(['Mechanic', 'Color', 'Primary %', 'Comp %', 'Delta'])
            for m in ordered_mechanics:
                for g in groups:
                    p1 = (group_mechanics[g][m] / group_totals[g] * 100) if group_totals[g] > 0 else 0
                    p2 = (comp_mechanics[g][m] / comp_totals[g] * 100) if comp_totals[g] > 0 else 0
                    writer.writerow([m, g, f"{p1:.1f}", f"{p2:.1f}", f"{p2-p1:.1f}"])
        else:
            writer.writerow(['Mechanic'] + list(groups))
            for m in ordered_mechanics:
                row = [m]
                for g in groups:
                    p = (group_mechanics[g][m] / group_totals[g] * 100) if group_totals[g] > 0 else 0
                    row.append(f"{p:.1f}")
                writer.writerow(row)

    else:
        # Table output
        title = "MECHANICAL COLOR PIE"
        if comp_mechanics:
            title += " (COMPARISON)"

        utils.print_header(title, count=total_cards, use_color=use_color)
        if comp_mechanics:
            print(f"  Comparison Dataset: {args.compare} ({total_comp} cards)\n")

        header = ["Mechanic"] + [g for g in groups]
        if use_color:
            header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

        rows = [header]
        for m in ordered_mechanics:
            row = [m]
            percents1 = []
            percents2 = []
            for g in groups:
                p1 = (group_mechanics[g][m] / group_totals[g] * 100) if group_totals[g] > 0 else 0
                percents1.append(p1)
                if comp_mechanics:
                    p2 = (comp_mechanics[g][m] / comp_totals[g] * 100) if comp_totals[g] > 0 else 0
                    percents2.append(p2)

            max_p1 = max(percents1) if percents1 else 0

            for i, g in enumerate(groups):
                p1 = percents1[i]
                if comp_mechanics:
                    p2 = percents2[i]
                    delta = p2 - p1
                    val_str = f"{p2:3.0f}%" # Show comparison value
                    if abs(delta) < 0.5:
                        display_val = "  - " if p2 == 0 else val_str
                    else:
                        color = utils.Ansi.GREEN if delta > 0 else utils.Ansi.RED
                        indicator = "▲" if delta > 0 else "▼"
                        if use_color:
                            display_val = utils.colorize(f"{val_str}{indicator}", color)
                        else:
                            display_val = f"{val_str}{indicator}"
                else:
                    if p1 > 0:
                        val_str = f"{p1:3.0f}%"
                        if use_color:
                            color = utils.Ansi.get_color_color(g)
                            if p1 == max_p1 and max_p1 > 0:
                                non_space = val_str.lstrip()
                                spaces = val_str[:len(val_str)-len(non_space)]
                                display_val = spaces + utils.colorize(non_space, color + utils.Ansi.UNDERLINE)
                            else:
                                display_val = utils.colorize(val_str, color)
                        else:
                            display_val = val_str
                    else:
                        display_val = "  - "
                row.append(display_val)
            rows.append(row)

        datalib.add_separator_row(rows)
        datalib.printrows(datalib.padrows(rows, aligns=['l'] + ['r']*len(groups)), indent=2)

    if not args.quiet:
        utils.print_operation_summary("Color Pie Analysis", total_cards + total_comp, 0)

if __name__ == "__main__":
    main()
