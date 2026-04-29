#!/usr/bin/env python3
import sys
import os
import argparse
from collections import OrderedDict

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import cardlib
import datalib

# Try to import tqdm for progress bars
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

def get_card_map(cards):
    """Groups cards by name for easier comparison."""
    m = OrderedDict()
    for c in cards:
        name = c.name.lower()
        if name not in m:
            m[name] = c
    return m

def compare_cards(c1, c2):
    """Compares two card objects and returns a list of differences."""
    diffs = []

    # 1. Mana Cost
    if c1.cost.format() != c2.cost.format():
        diffs.append(('Cost', c1.cost.format(), c2.cost.format()))

    # 2. Type Line
    if c1.get_type_line() != c2.get_type_line():
        diffs.append(('Type', c1.get_type_line(), c2.get_type_line()))

    # 3. Stats (P/T)
    s1 = c1._get_pt_display(include_parens=False)
    s2 = c2._get_pt_display(include_parens=False)
    if s1 != s2:
        diffs.append(('P/T', s1, s2))

    # 4. Loyalty / Defense
    l1 = c1._get_loyalty_display(include_parens=False)
    l2 = c2._get_loyalty_display(include_parens=False)
    if l1 != l2:
        diffs.append(('Loyalty/Defense', l1, l2))

    # 5. Rules Text
    t1 = c1.get_text(force_unpass=True)
    t2 = c2.get_text(force_unpass=True)
    if t1 != t2:
        diffs.append(('Text', t1, t2))

    # 6. Rarity
    if c1.rarity_name != c2.rarity_name:
        diffs.append(('Rarity', c1.rarity_name, c2.rarity_name))

    # B-side recursive comparison
    if c1.bside and c2.bside:
        b_diffs = compare_cards(c1.bside, c2.bside)
        for field, v1, v2 in b_diffs:
            diffs.append((f'B-Side {field}', v1, v2))
    elif c1.bside:
        diffs.append(('B-Side', 'Present', 'Missing'))
    elif c2.bside:
        diffs.append(('B-Side', 'Missing', 'Present'))

    return diffs

def main():
    parser = argparse.ArgumentParser(
        description="Compare two Magic: The Gathering card datasets and identify additions, removals, and modifications. "
                    "It highlights changes in mana cost, type, stats (P/T or loyalty), rules text, and rarity.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Compare two JSON datasets
  python3 scripts/mtg_diff.py data/OldSet.json data/NewSet.json

  # Compare encoded text against official data
  python3 scripts/mtg_diff.py data/AllPrintings.json generated_cards.txt

  # Only show a count summary, not detailed card diffs
  python3 scripts/mtg_diff.py data/AllPrintings.json generated.txt --summary-only

  # Filter comparison to only include cards matching a keyword
  python3 scripts/mtg_diff.py data/OldSet.json data/NewSet.json -g "Goblin"
""",
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('file1', help='Base card dataset (JSON, CSV, XML, or encoded text) to compare from.')
    io_group.add_argument('file2', help='Target card dataset to compare against the base.')

    # Group: Processing Options
    proc_group = parser.add_argument_group('Processing Options')
    proc_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    proc_group.add_argument('-q', '--quiet', action='store_true', help='Suppress the progress bar.')
    proc_group.add_argument('--summary-only', action='store_true',
                        help='Only show a count summary of additions, removals, and modifications.')

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

    # Color options
    color_group = parser.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color output.')

    args = parser.parse_args()

    # Determine if we should use color
    use_color = False
    if args.color is True:
        use_color = True
    elif args.color is None and sys.stdout.isatty():
        use_color = True

    # Load datasets
    if args.verbose:
        print(f"Loading {args.file1}...", file=sys.stderr)
    cards1 = jdecode.mtg_open_file(args.file1, verbose=args.verbose,
                                  grep=args.grep, vgrep=args.vgrep,
                                  grep_name=args.grep_name, vgrep_name=args.exclude_name,
                                  grep_types=args.grep_type, vgrep_types=args.exclude_type,
                                  grep_text=args.grep_text, vgrep_text=args.exclude_text,
                                  grep_cost=args.grep_cost, vgrep_cost=args.exclude_cost,
                                  grep_pt=args.grep_pt, vgrep_pt=args.exclude_pt,
                                  grep_loyalty=args.grep_loyalty, vgrep_loyalty=args.exclude_loyalty,
                                  sets=args.set, rarities=args.rarity,
                                  colors=args.colors, cmcs=args.cmc, pows=args.pow,
                                  tous=args.tou, loys=args.loy, mechanics=args.mechanic,
                                  identities=args.identity, id_counts=args.id_count)

    if args.verbose:
        print(f"Loading {args.file2}...", file=sys.stderr)
    cards2 = jdecode.mtg_open_file(args.file2, verbose=args.verbose,
                                  grep=args.grep, vgrep=args.vgrep,
                                  grep_name=args.grep_name, vgrep_name=args.exclude_name,
                                  grep_types=args.grep_type, vgrep_types=args.exclude_type,
                                  grep_text=args.grep_text, vgrep_text=args.exclude_text,
                                  grep_cost=args.grep_cost, vgrep_cost=args.exclude_cost,
                                  grep_pt=args.grep_pt, vgrep_pt=args.exclude_pt,
                                  grep_loyalty=args.grep_loyalty, vgrep_loyalty=args.exclude_loyalty,
                                  sets=args.set, rarities=args.rarity,
                                  colors=args.colors, cmcs=args.cmc, pows=args.pow,
                                  tous=args.tou, loys=args.loy, mechanics=args.mechanic,
                                  identities=args.identity, id_counts=args.id_count)

    map1 = get_card_map(cards1)
    map2 = get_card_map(cards2)

    added = []
    removed = []
    modified = []

    # Check for removals and modifications
    for name, c1 in tqdm(map1.items(), disable=args.quiet or len(map1) < 5, desc="Comparing datasets"):
        if name not in map2:
            removed.append(c1)
        else:
            c2 = map2[name]
            diffs = compare_cards(c1, c2)
            if diffs:
                modified.append((c2, diffs))

    # Check for additions
    for name, c2 in map2.items():
        if name not in map1:
            added.append(c2)

    # Output report
    added_color = utils.Ansi.BOLD + utils.Ansi.GREEN
    removed_color = utils.Ansi.BOLD + utils.Ansi.RED
    mod_color = utils.Ansi.BOLD + utils.Ansi.YELLOW

    utils.print_header("SUMMARY", use_color=use_color)
    total_distinct = len(map1.keys() | map2.keys())
    unchanged_count = len(map1.keys() & map2.keys()) - len(modified)

    rows = [[
        utils.colorize("Category", utils.Ansi.BOLD + utils.Ansi.UNDERLINE) if use_color else "Category",
        utils.colorize("Count", utils.Ansi.BOLD + utils.Ansi.UNDERLINE) if use_color else "Count",
        utils.colorize("Percent", utils.Ansi.BOLD + utils.Ansi.UNDERLINE) if use_color else "Percent",
        utils.colorize("Progress", utils.Ansi.BOLD + utils.Ansi.UNDERLINE) if use_color else "Progress"
    ]]

    summary_data = [
        ('Added', len(added), utils.Ansi.BOLD + utils.Ansi.GREEN),
        ('Removed', len(removed), utils.Ansi.BOLD + utils.Ansi.RED),
        ('Modified', len(modified), utils.Ansi.BOLD + utils.Ansi.YELLOW),
        ('Unchanged', unchanged_count, utils.Ansi.BOLD)
    ]

    for label, count, color in summary_data:
        percent = (count / total_distinct * 100) if total_distinct > 0 else 0
        bar = datalib.get_bar_chart(percent, use_color, color=color)

        if use_color:
            label_str = utils.colorize(label, color)
            count_str = datalib.color_count(count, use_color, color)
        else:
            label_str = label
            count_str = str(count)

        rows.append([label_str, count_str, f"{percent:5.1f}%", bar])

    datalib.printrows(datalib.padrows(rows, aligns=['l', 'r', 'r', 'l']), indent=2)
    print()

    if args.summary_only:
        return

    if removed:
        utils.print_header("REMOVED CARDS", count=len(removed), use_color=use_color)
        for c in removed:
            name = c.name
            if use_color:
                name = utils.colorize(name, removed_color)
            print(f"  - {name}")
        print()

    if added:
        utils.print_header("ADDED CARDS", count=len(added), use_color=use_color)
        for c in added:
            name = c.name
            if use_color:
                name = utils.colorize(name, added_color)
            print(f"  - {name}")
        print()

    if modified:
        utils.print_header("MODIFIED CARDS", count=len(modified), use_color=use_color)
        for c, diffs in modified:
            name = c.name
            if use_color:
                name = utils.colorize(name, mod_color)
            print(f"  * {name}")

            diff_rows = []
            for field, old, new in diffs:
                field_str = f"{field}:"
                if use_color:
                    field_str = utils.colorize(field_str, utils.Ansi.CYAN)
                    old_str = utils.colorize(str(old), utils.Ansi.RED)
                    new_str = utils.colorize(str(new), utils.Ansi.GREEN)
                else:
                    old_str = str(old)
                    new_str = str(new)
                diff_rows.append([f"    {field_str}", old_str, "->", new_str])

            for row in datalib.padrows(diff_rows, aligns=['l', 'r', 'c', 'l']):
                print(row)
        print()

    # Provide clear feedback on operation completion
    utils.print_operation_summary("Comparison", len(map2), 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
