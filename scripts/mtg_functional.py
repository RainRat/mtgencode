#!/usr/bin/env python3
import sys
import os
import argparse
import json
import csv
from collections import defaultdict, OrderedDict

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import datalib
from titlecase import titlecase

def get_functional_key(card):
    """
    Generates a unique key for a card based on its functional attributes.
    Names are excluded to identify functional reprints.
    """
    # Core attributes
    cost = card.cost.encode()
    # Sort types for consistency, though cardlib usually handles this
    types = (tuple(sorted(card.supertypes)),
             tuple(sorted(card.types)),
             tuple(sorted(card.subtypes)))
    stats = (card.pt, card.loyalty)

    # Rules text (encoded format preserves @ marker for self-reference)
    # Card initialization with linetrans=True (default) ensures canonical line order.
    text = card.text.encode()

    key = (cost, types, stats, text)

    # Recursive key for multi-faced cards
    if card.bside:
        key = (key, get_functional_key(card.bside))

    return key

def main():
    parser = argparse.ArgumentParser(
        description="Identify and group 'functional reprints' (cards with different names but identical stats and abilities).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Functional reprints are identified by comparing:
  - Mana Cost
  - Type Line (Supertypes, Types, Subtypes)
  - Stats (Power, Toughness, Loyalty, Defense)
  - Rules Text (Normalized, with self-references standardized)

Usage Examples:
  # List all functional reprints in AllPrintings.json
  python3 scripts/mtg_functional.py data/AllPrintings.json

  # Create a deduplicated dataset (one card per functional group)
  python3 scripts/mtg_functional.py data/AllPrintings.json --dedupe unique_cards.json

  # Find functional reprints of Goblins
  python3 scripts/mtg_functional.py data/AllPrintings.json --grep "Goblin"
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, XML, or encoded text). Defaults to stdin (-). '
                             'If stdin is a terminal, it attempts to use data/AllPrintings.json.')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Optional path to save the results.')

    # Group: Output Format
    fmt_group_title = parser.add_argument_group('Output Format')
    fmt_group = fmt_group_title.add_mutually_exclusive_group()
    fmt_group.add_argument('--table', action='store_true', help='Display groups in a formatted table (Default).')
    fmt_group.add_argument('--json', action='store_true', help='Output groups as JSON.')
    fmt_group.add_argument('--csv', action='store_true', help='Output groups as CSV.')
    fmt_group.add_argument('--dedupe', action='store_true',
                           help='Output a JSON file containing the full dataset with functional duplicates removed.')

    # Group: Filtering Options (Standard across tools)
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('--grep', action='append',
                        help='Only include cards matching a search pattern.')
    filter_group.add_argument('--vgrep', '--exclude', action='append',
                        help='Skip cards matching a search pattern.')
    filter_group.add_argument('--set', action='append', help='Only include cards from specific sets.')
    filter_group.add_argument('--rarity', action='append', help='Only include cards of specific rarities.')
    filter_group.add_argument('--colors', action='append', help='Only include cards of specific colors.')
    filter_group.add_argument('--cmc', action='append', help='Only include cards with specific CMC values.')
    filter_group.add_argument('--pow', '--power', action='append', dest='pow', help='Only include cards with specific Power values.')
    filter_group.add_argument('--tou', '--toughness', action='append', dest='tou', help='Only include cards with specific Toughness values.')
    filter_group.add_argument('--loy', '--loyalty', '--defense', action='append', dest='loy', help='Only include cards with specific Loyalty or Defense values.')
    filter_group.add_argument('--mechanic', action='append', help='Only include cards with specific mechanics.')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    debug_group.add_argument('-q', '--quiet', action='store_true', help='Suppress status messages.')
    debug_group.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color output.')
    debug_group.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color output.')

    args = parser.parse_args()

    # UX Improvement: Default Dataset
    # If we are reading from stdin but it's an interactive terminal, use AllPrintings.json if it exists.
    if args.infile == '-' and sys.stdin.isatty():
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

    # Determine if we should use color
    use_color = False
    if args.color is True:
        use_color = True
    elif args.color is None and sys.stdout.isatty() and not (args.json or args.csv or args.dedupe):
        use_color = True

    # Load and filter cards
    cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose,
                                  grep=args.grep, vgrep=args.vgrep,
                                  sets=args.set, rarities=args.rarity,
                                  colors=args.colors, cmcs=args.cmc,
                                  pows=args.pow, tous=args.tou, loys=args.loy,
                                  mechanics=args.mechanic)

    if not cards:
        if not args.quiet:
            print("No cards found matching the criteria.", file=sys.stderr)
        return

    # Group cards by functional key
    functional_groups = defaultdict(list)
    for card in cards:
        key = get_functional_key(card)
        functional_groups[key].append(card)

    # Filter for groups that are actually reprints (multiple different names)
    reprint_groups = []
    unique_representative_cards = []

    for key in sorted(functional_groups.keys(), key=lambda x: str(x)):
        group = functional_groups[key]

        # De-duplicate names within the group (e.g. same card from different sets)
        name_map = OrderedDict()
        for c in group:
            name_lower = c.name.lower()
            if name_lower not in name_map:
                name_map[name_lower] = c

        distinct_cards = list(name_map.values())
        unique_representative_cards.append(distinct_cards[0])

        if len(distinct_cards) > 1:
            reprint_groups.append(distinct_cards)

    # Set default format
    if not (args.table or args.json or args.csv or args.dedupe):
        args.table = True

    output_f = sys.stdout
    if args.outfile:
        output_f = open(args.outfile, 'w', encoding='utf-8')

    try:
        if args.dedupe:
            # Output unique cards as JSON
            results = [c.to_dict() for c in unique_representative_cards]
            output_f.write(json.dumps(results, indent=2) + '\n')

        elif args.json:
            # Output groups as JSON
            results = []
            for group in reprint_groups:
                results.append({
                    'names': [titlecase(c.name) for c in group],
                    'card_data': group[0].to_dict()
                })
            output_f.write(json.dumps(results, indent=2) + '\n')

        elif args.csv:
            # Output groups as CSV
            writer = csv.writer(output_f)
            writer.writerow(['Names', 'Cost', 'Type', 'Stats', 'Rules Text'])
            for group in reprint_groups:
                c = group[0]
                names = " // ".join([titlecase(card.name) for card in group])
                cost = c.cost.format()
                ctype = c.get_type_line()
                stats = c._get_pt_display(include_parens=False) or c._get_loyalty_display(include_parens=False)
                text = c.get_text(force_unpass=True).replace('\n', ' \\n ')
                writer.writerow([names, cost, ctype, stats, text])

        else: # --table
            if not reprint_groups:
                if not args.quiet:
                    print("No functional reprints found.", file=sys.stderr)
                return

            utils.print_header("FUNCTIONAL REPRINT GROUPS", count=len(reprint_groups), file=output_f, use_color=use_color)

            rows = []
            header = ["Names", "Cost", "Type", "Stats"]
            if use_color:
                header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]
            rows.append(header)

            for group in reprint_groups:
                c = group[0]
                names = ", ".join([titlecase(card.name) for card in group])
                if use_color:
                    names = utils.colorize(names, utils.Ansi.BOLD + utils.Ansi.CYAN)

                cost = c.cost.format(ansi_color=use_color)
                ctype = c.get_type_line()
                if use_color:
                    ctype = utils.colorize(ctype, utils.Ansi.GREEN)

                stats = c._get_pt_display(ansi_color=use_color, include_parens=False)
                if not stats:
                    stats = c._get_loyalty_display(ansi_color=use_color, include_parens=False)

                rows.append([names, cost, ctype, stats])

            datalib.add_separator_row(rows)
            for row in datalib.padrows(rows, aligns=['l', 'l', 'l', 'r']):
                output_f.write("  " + row + '\n')

    finally:
        if args.outfile:
            output_f.close()

    if not args.quiet:
        utils.print_operation_summary("Functional check", len(reprint_groups), 0)


if __name__ == "__main__":
    main()
