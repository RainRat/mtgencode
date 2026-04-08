#!/usr/bin/env python3
import sys
import os
import argparse

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import datalib
import cardlib
from datalib import Datamine

def get_stats_for_file(path, args):
    """Loads cards from a file and returns a Datamine object."""
    search_stats = {}
    cards = jdecode.mtg_open_file(path, verbose=args.verbose, linetrans=not args.nolinetrans,
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
                                  exclude_sets=lambda x: False,
                                  exclude_types=lambda x: False,
                                  exclude_layouts=lambda x: False,
                                  shuffle=args.shuffle, seed=args.seed,
                                  decklist_file=args.deck,
                                  stats=search_stats,
                                  booster=args.booster,
                                  box=args.box)

    if args.limit > 0:
        cards = cards[:args.limit]

    return Datamine(cards, search_stats=search_stats)

def format_delta(val, base_val, is_percent=False, use_color=False, reverse_color=False):
    """Formats the difference between two values with an indicator."""
    delta = val - base_val
    if abs(delta) < 1e-6:
        return " -- "

    sign = "+" if delta > 0 else ""
    suffix = "%" if is_percent else ""
    res = f"{sign}{delta:.1f}{suffix}"

    if use_color:
        # For stats like CMC, usually lower is "better" but it depends.
        # For simplicity, we'll just color positive green and negative red unless reversed.
        is_good = delta > 0 if not reverse_color else delta < 0
        color = utils.Ansi.BOLD + (utils.Ansi.GREEN if is_good else utils.Ansi.RED)
        res = utils.colorize(res, color)

    return res

def main():
    parser = argparse.ArgumentParser(
        description="Compare statistics of multiple Magic: The Gathering card datasets side-by-side."
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infiles', nargs='+',
                        help='Input card data files to compare (JSON, CSV, encoded text, etc.).')

    # Group: Content Formatting
    enc_group = parser.add_argument_group('Content Formatting')
    enc_group.add_argument('--nolabel', action='store_true',
                        help="Input file does not have field labels (like '|cost|' or '|text|').")
    enc_group.add_argument('--nolinetrans', action='store_true',
                        help='Input file does not use automatic line reordering.')

    # Group: Data Processing
    proc_group = parser.add_argument_group('Data Processing')
    proc_group.add_argument('-n', '--limit', type=int, default=0,
                        help='Only process the first N cards from each input.')
    proc_group.add_argument('--shuffle', action='store_true',
                        help='Randomize the order of cards before analyzing.')
    proc_group.add_argument('--seed', type=int,
                        help='Seed for the random number generator.')
    proc_group.add_argument('--sample', type=int, default=0,
                        help='Pick N random cards from each input (shorthand for --shuffle --limit N).')

    # Group: Filtering Options
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('--booster', type=int, default=0,
                        help='Simulate opening N booster packs. Distribution: 10 Common, 3 Uncommon, 1 Rare/Mythic, 1 Basic Land. Shuffles by default.')
    filter_group.add_argument('--box', type=int, default=0,
                        help='Simulate opening N booster boxes (36 packs each). Shuffles by default.')
    filter_group.add_argument('--grep', action='append',
                        help='Only include cards matching a search pattern (checks name, typeline, text, cost, and stats). Use multiple times for AND logic.')
    filter_group.add_argument('--grep-name', action='append',
                        help='Only include cards whose name matches a search pattern.')
    filter_group.add_argument('--exclude-name', action='append',
                        help='Exclude cards whose name matches a search pattern.')
    filter_group.add_argument('--grep-type', action='append',
                        help='Only include cards whose typeline matches a search pattern.')
    filter_group.add_argument('--exclude-type', action='append',
                        help='Exclude cards whose typeline matches a search pattern.')
    filter_group.add_argument('--grep-text', action='append',
                        help='Only include cards whose rules text matches a search pattern.')
    filter_group.add_argument('--exclude-text', action='append',
                        help='Exclude cards whose rules text matches a search pattern.')
    filter_group.add_argument('--grep-cost', action='append',
                        help='Only include cards whose mana cost matches a search pattern.')
    filter_group.add_argument('--exclude-cost', action='append',
                        help='Exclude cards whose mana cost matches a search pattern.')
    filter_group.add_argument('--grep-pt', action='append',
                        help='Only include cards whose power/toughness matches a search pattern.')
    filter_group.add_argument('--exclude-pt', action='append',
                        help='Exclude cards whose power/toughness matches a search pattern.')
    filter_group.add_argument('--grep-loyalty', action='append',
                        help='Only include cards whose loyalty/defense matches a search pattern.')
    filter_group.add_argument('--exclude-loyalty', action='append',
                        help='Exclude cards whose loyalty/defense matches a search pattern.')
    filter_group.add_argument('--vgrep', '--exclude', action='append', dest='vgrep',
                        help='Skip cards matching a search pattern (checks name, typeline, text, cost, and stats). Use multiple times for OR logic.')
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
                        help='Filter cards using a standard MTG decklist file. Also multiplies cards in the output based on their counts in the decklist.')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true',
                        help='Enable detailed status messages.')

    # Color options
    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None,
                        help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color',
                        help='Disable ANSI color output.')

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

    # Load all datasets
    mines = []
    for f in args.infiles:
        if args.verbose:
            print(f"Analyzing {f}...", file=sys.stderr)
        mines.append(get_stats_for_file(f, args))

    if not mines:
        return

    base_mine = mines[0]
    base_data = base_mine.to_dict()

    # Header row
    filenames = [os.path.basename(f)[:15] for f in args.infiles]
    header = ["Metric", filenames[0]]
    for i in range(1, len(filenames)):
        header.append(filenames[i])
        header.append("Delta")

    if use_color:
        header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

    rows = [header]

    def add_metric_row(label, key_path, is_percent=False, reverse_color=False, formatter=None):
        row = [label]

        # Get base value
        try:
            val = base_data
            for k in key_path:
                val = val[k]
            base_val = float(val)
        except (KeyError, TypeError, ValueError):
            base_val = 0.0

        row.append(formatter(base_val) if formatter else f"{base_val:.1f}{'%' if is_percent else ''}")

        for i in range(1, len(mines)):
            data = mines[i].to_dict()
            try:
                val = data
                for k in key_path:
                    val = val[k]
                current_val = float(val)
            except (KeyError, TypeError, ValueError):
                current_val = 0.0

            row.append(formatter(current_val) if formatter else f"{current_val:.1f}{'%' if is_percent else ''}")
            row.append(format_delta(current_val, base_val, is_percent, use_color, reverse_color))

        rows.append(row)

    def add_index_percent_row(label, index_name, key, use_label_as_key=False):
        row = [label]
        target_key = label if use_label_as_key else key

        def get_pct(mine_obj):
            idx = mine_obj.indices.get(index_name, {})
            count = len(idx.get(target_key, []))
            total = len(mine_obj.allcards)
            return (count / total * 100) if total > 0 else 0

        base_pct = get_pct(mines[0])
        row.append(f"{base_pct:5.1f}%")

        for i in range(1, len(mines)):
            current_pct = get_pct(mines[i])
            row.append(f"{current_pct:5.1f}%")
            row.append(format_delta(current_pct, base_pct, is_percent=True, use_color=use_color))

        rows.append(row)

    def add_separator(title):
        title_str = utils.colorize(f"--- {title} ---", utils.Ansi.BOLD + utils.Ansi.CYAN) if use_color else f"--- {title} ---"
        rows.append([title_str] + [""] * (len(header) - 1))

    # General Stats
    add_separator("General")
    row_count = ["Total Cards", str(len(base_mine.allcards))]
    for i in range(1, len(mines)):
        row_count.append(str(len(mines[i].allcards)))
        delta = len(mines[i].allcards) - len(base_mine.allcards)
        delta_str = f"{delta:+d}"
        if use_color:
            delta_str = utils.colorize(delta_str, utils.Ansi.BOLD + (utils.Ansi.CYAN if delta != 0 else ""))
        row_count.append(delta_str)
    rows.append(row_count)

    def add_count_pct_row(label, key_path):
        """Helper to add a row representing a count as a percentage of its dataset's total."""
        row = [label]
        base_total = len(mines[0].allcards)
        base_val = base_data
        for k in key_path:
            base_val = base_val[k]
        base_pct = (base_val / base_total * 100) if base_total > 0 else 0
        row.append(f"{base_pct:.1f}%")
        for i in range(1, len(mines)):
            total = len(mines[i].allcards)
            val = mines[i].to_dict()
            for k in key_path:
                val = val[k]
            pct = (val / total * 100) if total > 0 else 0
            row.append(f"{pct:.1f}%")
            row.append(format_delta(pct, base_pct, is_percent=True, use_color=use_color))
        rows.append(row)

    add_count_pct_row("Valid %", ["counts", "valid"])

    # Unique Name %
    row_unique = ["Unique Name %"]
    base_unique = (len(mines[0].by_name) / len(mines[0].allcards) * 100) if mines[0].allcards else 0
    row_unique.append(f"{base_unique:.1f}%")
    for i in range(1, len(mines)):
        unique = (len(mines[i].by_name) / len(mines[i].allcards) * 100) if mines[i].allcards else 0
        row_unique.append(f"{unique:.1f}%")
        row_unique.append(format_delta(unique, base_unique, is_percent=True, use_color=use_color))
    rows.append(row_unique)

    # Average Stats
    add_separator("Averages")
    add_metric_row("Avg CMC", ["stats", "avg_cmc"], reverse_color=True)
    add_metric_row("Avg Power", ["stats", "avg_power"])
    add_metric_row("Avg Toughness", ["stats", "avg_toughness"])

    # Color Distribution
    add_separator("Colors")
    for c in 'WUBRG':
        add_index_percent_row(f"{c} %", "by_color_inclusive", c)
    add_index_percent_row("Colorless %", "by_color_inclusive", "A")
    # Fix Multi % row
    row_multi = ["Multi %"]
    def get_multi_pct(mine_obj):
        count = sum(len(v) for k, v in mine_obj.by_color_count.items() if isinstance(k, int) and k > 1)
        total = len(mine_obj.allcards)
        return (count / total * 100) if total > 0 else 0
    base_multi = get_multi_pct(mines[0])
    row_multi.append(f"{base_multi:5.1f}%")
    for i in range(1, len(mines)):
        multi = get_multi_pct(mines[i])
        row_multi.append(f"{multi:5.1f}%")
        row_multi.append(format_delta(multi, base_multi, is_percent=True, use_color=use_color))
    rows.append(row_multi)

    # Type Distribution
    add_separator("Types")
    for t in ["Creature", "Instant", "Sorcery", "Enchantment", "Artifact", "Planeswalker", "Land"]:
        add_index_percent_row(f"{t} %", "by_type_inclusive", t.lower())

    # Rarity Distribution
    add_separator("Rarities")
    for r in ["Common", "Uncommon", "Rare", "Mythic"]:
        add_index_percent_row(f"{r} %", "by_rarity", r.lower())

    # Print Table
    print(utils.colorize("DATASET COMPARISON", utils.Ansi.BOLD + utils.Ansi.CYAN + utils.Ansi.UNDERLINE) if use_color else "=== DATASET COMPARISON ===")

    col_widths = datalib.get_col_widths(rows)
    separator = ['-' * w for w in col_widths]
    rows.insert(1, separator)

    aligns = ['l'] + ['r'] * (len(header) - 1)
    datalib.printrows(datalib.padrows(rows, aligns=aligns), indent=2)

    # Summary
    utils.print_operation_summary("Comparison", len(mines), 0)

if __name__ == "__main__":
    main()
