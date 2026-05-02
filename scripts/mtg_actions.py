#!/usr/bin/env python3
import sys
import os
import argparse
import json
import csv
import re
from collections import defaultdict, Counter

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import datalib
import cardlib

# Categorization patterns
# These look for functional "actions" in rules text.
ACTION_CATEGORIES = {
    'Removal': [
        r'\bdestroy\b',
        r'\bexile target\b',
        r'sacrifice (a|target|an)\b',
        r'deals? \d+ damage to (target|each) (creature|planeswalker|permanent)',
        r'deals? &[\^]+ damage to (target|each) (creature|planeswalker|permanent)',
        r'return (target|each) [^:]* to (its|their) owner\'s hand'
    ],
    'Protection': [
        r'\bhexproof\b',
        r'\bindestructible\b',
        r'\bward\b',
        r'\bprotection from\b',
        r'\bshroud\b',
        r'\bregenerate\b'
    ],
    'Buffs': [
        r'gets? \+&[\^]*/\+&[\^]*',
        r'put (a|&[\^]+) \+&[\^]*/\+&[\^]* counter',
        r'target creature gets \+',
        r'creatures you control get \+'
    ],
    'Card Advantage': [
        r'\bdraw(s|ing)? (a|&[\^]+) cards?\b',
        r'\bsearch your library\b',
        r'\breturn (target|a) card from your graveyard\b'
    ],
    'Disruption': [
        r'\bdiscard(s|ing)? (a|&[\^]+)?\b',
        r'\buncast target\b', # 'uncast' is the project's internal term for counterspell
        r'\btap target\b',
        r'can\'t attack or block'
    ]
}

def get_card_actions(card):
    """Identifies functional actions present on a card."""
    # Use unpassed text for better pattern matching
    text = card.get_text(force_unpass=True).lower()
    # Also check encoded text for unary patterns
    text_enc = card.text.encode().lower()

    actions = set()
    for category, patterns in ACTION_CATEGORIES.items():
        for pattern in patterns:
            if re.search(pattern, text) or re.search(pattern, text_enc):
                actions.add(category)
                break

    # Recursive for b-sides
    if card.bside:
        actions.update(get_card_actions(card.bside))

    return actions

def main():
    parser = argparse.ArgumentParser(
        description="Analyze functional card effects (Removal, Protection, Buffs, etc.) in a dataset.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Analyze actions for a specific set
  python3 scripts/mtg_actions.py data/AllPrintings.json --set MOM

  # Compare interaction density of Red vs Blue
  python3 scripts/mtg_actions.py data/AllPrintings.json --colors R
  python3 scripts/mtg_actions.py data/AllPrintings.json --colors U
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data. Defaults to stdin (-).')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save results.')

    # Group: Output Format
    fmt_group = io_group.add_mutually_exclusive_group()
    fmt_group.add_argument('--table', action='store_true', help='Generate table (Default).')
    fmt_group.add_argument('--json', action='store_true', help='Generate JSON.')
    fmt_group.add_argument('--csv', action='store_true', help='Generate CSV.')

    # Group: Filtering Options (Standard)
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('-g', '--grep', action='append', help='Pattern match cards.')
    filter_group.add_argument('--set', action='append', help='Specific sets.')
    filter_group.add_argument('--rarity', action='append', help='Specific rarities.')
    filter_group.add_argument('--colors', action='append', help='Specific colors.')
    filter_group.add_argument('--cmc', action='append', help='Specific CMC.')
    filter_group.add_argument('--limit', type=int, default=0, help='Limit processing.')
    filter_group.add_argument('--sample', type=int, default=0, help='Random sample.')

    # Group: Logging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Verbose output.')
    debug_group.add_argument('-q', '--quiet', action='store_true', help='Quiet output.')

    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None, help='Force color.')
    color_group.add_argument('--no-color', action='store_false', dest='color', help='Disable color.')

    args = parser.parse_args()

    # Smart Positional Argument Handling
    if args.infile != '-' and not os.path.exists(args.infile):
        # Swap if it looks like a query
        if not args.grep:
            args.grep = [args.infile]
            args.infile = '-'
            # Try to find default dataset if stdin is tty
            if sys.stdin.isatty():
                default_data = 'data/AllPrintings.json'
                if os.path.exists(default_data):
                    args.infile = default_data

    # Load cards
    cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose,
                                  grep=args.grep, sets=args.set, rarities=args.rarity,
                                  colors=args.colors, cmcs=args.cmc,
                                  shuffle=(args.sample > 0))

    if args.sample > 0:
        cards = cards[:args.sample]
    elif args.limit > 0:
        cards = cards[:args.limit]

    if not cards:
        if not args.quiet:
            print("No cards found.", file=sys.stderr)
        return

    # Analysis
    action_counts = Counter()
    color_actions = defaultdict(Counter)

    for card in cards:
        actions = get_card_actions(card)
        for action in actions:
            action_counts[action] += 1
            # Track by primary color
            primary_colors = card.cost.colors or ['C']
            for color in primary_colors:
                color_actions[color][action] += 1

    # Output detection
    if not (args.json or args.csv or args.table):
        if args.outfile:
            if args.outfile.endswith('.json'): args.json = True
            elif args.outfile.endswith('.csv'): args.csv = True
        else:
            args.table = True

    use_color = args.color if args.color is not None else (sys.stdout.isatty() and not (args.json or args.csv))

    results = {
        'total_cards': len(cards),
        'action_summary': dict(action_counts),
        'color_breakdown': {c: dict(counts) for c, counts in color_actions.items()}
    }

    output_f = open(args.outfile, 'w', encoding='utf-8') if args.outfile else sys.stdout

    try:
        if args.json:
            output_f.write(json.dumps(results, indent=2) + '\n')
        elif args.csv:
            writer = csv.writer(output_f)
            writer.writerow(['Category', 'Action', 'Count', 'Percent'])
            for action, count in action_counts.most_common():
                writer.writerow(['Global', action, count, f"{(count/len(cards)*100):.1f}%"])
        else:
            utils.print_header("CARD ACTION ANALYSIS", count=len(cards), use_color=use_color, file=output_f)

            header = ["Action Category", "Count", "Percent", "Frequency"]
            if use_color:
                header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

            rows = [header]
            for action, count in action_counts.most_common():
                percent = (count / len(cards) * 100)
                bar = datalib.get_bar_chart(percent, use_color, color=utils.Ansi.BOLD + utils.Ansi.CYAN)
                rows.append([
                    utils.colorize(action, utils.Ansi.CYAN) if use_color else action,
                    datalib.color_count(count, use_color),
                    f"{percent:5.1f}%",
                    bar
                ])
            datalib.add_separator_row(rows)
            datalib.printrows(datalib.padrows(rows, aligns=['l', 'r', 'r', 'l']), indent=4)
            print("", file=output_f)

            # Color Breakdown Table
            print(f"  {datalib.color_line('Actions by Color (Frequency %):', use_color)}", file=output_f)
            c_header = ["Action", "W", "U", "B", "R", "G", "C"]
            if use_color:
                c_header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in c_header]

            c_rows = [c_header]
            for action in sorted(ACTION_CATEGORIES.keys()):
                row = [action]
                for color in "WUBRGC":
                    total_in_color = sum(1 for c in cards if (c.cost.colors or ['C'])[0] == color)
                    count = color_actions[color][action]
                    percent = (count / total_in_color * 100) if total_in_color > 0 else 0

                    val_str = f"{percent:4.0f}%"
                    if use_color and percent > 0:
                        val = utils.colorize(val_str, utils.Ansi.get_color_color(color))
                    elif percent > 0:
                        val = val_str
                    else:
                        val = "  - "
                    row.append(val)
                c_rows.append(row)
            datalib.add_separator_row(c_rows)
            datalib.printrows(datalib.padrows(c_rows, aligns=['l', 'r', 'r', 'r', 'r', 'r', 'r']), indent=4)

    finally:
        if args.outfile:
            output_f.close()

if __name__ == "__main__":
    main()
