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
from cardlib import RECOGNIZED_MECHANICS

DIMENSIONS = {
    'color': {
        'label': 'Color Identity',
        'keys': 'WUBRGAM',
        'fn': lambda c: get_color_group(c),
        'formatter': lambda k, use_color: utils.colorize(k, utils.Ansi.get_color_color(k)) if use_color else k
    },
    'rarity': {
        'label': 'Rarity',
        'keys': ['Common', 'Uncommon', 'Rare', 'Mythic', 'Special', 'Basic Land'],
        'fn': lambda c: c.rarity_name.title(),
        'formatter': lambda k, use_color: utils.colorize(k, utils.Ansi.get_rarity_color(k)) if use_color else k
    },
    'type': {
        'label': 'Card Type',
        'keys': ["Creature", "Instant", "Sorcery", "Enchantment", "Artifact", "Planeswalker", "Land", "Battle", "Other"],
        'fn': lambda c: get_card_type(c),
        'formatter': lambda k, use_color: format_type(k, use_color)
    },
    'cmc': {
        'label': 'CMC',
        'keys': ['0', '1', '2', '3', '4', '5', '6', '7+'],
        'fn': lambda c: bucket_numeric(c.cost.cmc),
        'formatter': lambda k, use_color: utils.colorize(k, utils.Ansi.CYAN) if use_color else k
    },
    'power': {
        'label': 'Power',
        'keys': ['0', '1', '2', '3', '4', '5', '6', '7+'],
        'fn': lambda c: bucket_numeric(utils.from_unary_single(c.pt_p)),
        'formatter': lambda k, use_color: utils.colorize(k, utils.Ansi.RED) if use_color else k
    },
    'toughness': {
        'label': 'Toughness',
        'keys': ['0', '1', '2', '3', '4', '5', '6', '7+'],
        'fn': lambda c: bucket_numeric(utils.from_unary_single(c.pt_t)),
        'formatter': lambda k, use_color: utils.colorize(k, utils.Ansi.RED) if use_color else k
    },
    'loyalty': {
        'label': 'Loyalty/Defense',
        'keys': ['0', '1', '2', '3', '4', '5', '6', '7+'],
        'fn': lambda c: bucket_numeric(utils.from_unary_single(c.loyalty)),
        'formatter': lambda k, use_color: utils.colorize(k, utils.Ansi.RED) if use_color else k
    },
    'mechanic': {
        'label': 'Mechanic',
        'keys': RECOGNIZED_MECHANICS,
        'fn': lambda c: list(c.mechanics),
        'is_multi': True,
        'formatter': lambda k, use_color: utils.colorize(k, utils.Ansi.CYAN) if use_color else k
    }
}

def get_color_group(card):
    identity = card.color_identity
    if len(identity) > 1: return 'M'
    if len(identity) == 1: return identity[0]
    return 'A'

def get_card_type(card):
    for t in DIMENSIONS['type']['keys'][:-1]:
        if card._has_type(t): return t
    return "Other"

def format_type(t, use_color):
    if not use_color: return t
    color = utils.Ansi.CYAN
    if t == "Creature": color = utils.Ansi.GREEN
    elif t == "Land": color = utils.Ansi.BOLD
    return utils.colorize(t, color)

def bucket_numeric(val):
    if val is None: return None
    try:
        v = int(float(val))
        if v < 0: v = 0
        if v >= 7: return '7+'
        return str(v)
    except (ValueError, TypeError):
        return None

def main():
    parser = argparse.ArgumentParser(
        description="Generate a 2D cross-tabulation grid for Magic: The Gathering card datasets.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available Dimensions:
  color, rarity, type, cmc, power, toughness, loyalty, mechanic

Usage Examples:
  # Analyze Type vs Color Identity for a specific set
  python3 scripts/mtg_grid.py type color --set MOM

  # Analyze Rarity vs CMC
  python3 scripts/mtg_grid.py rarity cmc data/AllPrintings.json

  # Analyze Mechanic vs Color Identity for rares
  python3 scripts/mtg_grid.py mechanic color --rarity rare

  # Export CMC vs Power distribution for creatures to CSV
  python3 scripts/mtg_grid.py cmc power --grep-type "Creature" --csv
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('row_dim', choices=DIMENSIONS.keys(), help='Dimension to use for rows.')
    io_group.add_argument('col_dim', choices=DIMENSIONS.keys(), help='Dimension to use for columns.')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, XML, or encoded text). Defaults to stdin (-). '
                             'If stdin is a terminal, it attempts to use data/AllPrintings.json.')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save results. If not provided, results print to the console.')

    # Group: Output Format
    fmt_group_title = parser.add_argument_group('Output Format')
    fmt_group = fmt_group_title.add_mutually_exclusive_group()
    fmt_group.add_argument('--table', action='store_true', help='Generate a formatted table (Default).')
    fmt_group.add_argument('-j', '--json', action='store_true', help='Generate a JSON file.')
    fmt_group.add_argument('--csv', action='store_true', help='Generate a CSV file.')

    # Group: Filtering Options (Standard)
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('-g', '--grep', action='append', help='Only include cards matching a search pattern.')
    filter_group.add_argument('--set', action='append', help='Only include cards from specific sets.')
    filter_group.add_argument('--rarity', action='append', help='Only include cards of specific rarities.')
    filter_group.add_argument('--colors', action='append', help='Only include cards of specific colors.')
    filter_group.add_argument('--identity', action='append', help='Only include cards with specific identities.')
    filter_group.add_argument('--cmc', action='append', help='Only include cards with specific CMC values.')
    filter_group.add_argument('--pow', '--power', action='append', dest='pow', help='Only include cards with specific Power.')
    filter_group.add_argument('--tou', '--toughness', action='append', dest='tou', help='Only include cards with specific Toughness.')
    filter_group.add_argument('--mechanic', action='append', help='Only include cards with specific mechanics.')
    filter_group.add_argument('-n', '--limit', type=int, default=0, help='Only process the first N cards.')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    debug_group.add_argument('-q', '--quiet', action='store_true', help='Suppress status messages.')

    # Color options
    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color output.')

    args = parser.parse_args()

    # Smart Positional Argument Handling
    if args.infile != '-' and not os.path.exists(args.infile):
        if not args.grep:
            args.grep = [args.infile]
            args.infile = '-'

    # Default Dataset
    if args.infile == '-' and sys.stdin.isatty():
        script_dir = os.path.dirname(os.path.realpath(__file__))
        default_data = os.path.join(script_dir, '../data/AllPrintings.json')
        if os.path.exists(default_data):
            args.infile = default_data

    # Format detection
    if not (args.json or args.csv or args.table):
        if args.outfile:
            if args.outfile.endswith('.json'): args.json = True
            elif args.outfile.endswith('.csv'): args.csv = True
            else: args.table = True
        else:
            args.table = True

    # Color detection
    use_color = args.color if args.color is not None else (sys.stdout.isatty() and not (args.json or args.csv))

    # Load data
    cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose, grep=args.grep,
                                  sets=args.set, rarities=args.rarity, colors=args.colors, identities=args.identity,
                                  cmcs=args.cmc, pows=args.pow, tous=args.tou, mechanics=args.mechanic)
    if args.limit > 0:
        cards = cards[:args.limit]

    if not cards:
        if not args.quiet:
            print("No cards found matching criteria.", file=sys.stderr)
        return

    # Dimensions
    r_dim = DIMENSIONS[args.row_dim]
    c_dim = DIMENSIONS[args.col_dim]

    # Analysis
    matrix = defaultdict(Counter)
    row_totals = Counter()
    col_totals = Counter()
    grand_total = 0

    for card in cards:
        r_vals = r_dim['fn'](card)
        c_vals = c_dim['fn'](card)

        if not isinstance(r_vals, list): r_vals = [r_vals]
        if not isinstance(c_vals, list): c_vals = [c_vals]

        # Multi-value dimensions (like mechanics) can count multiple times
        # But we only want to count the card once for grand total
        grand_total += 1

        for rv in r_vals:
            if rv is None: continue
            row_totals[rv] += 1
            for cv in c_vals:
                if cv is None: continue
                matrix[rv][cv] += 1

        for cv in c_vals:
            if cv is None: continue
            col_totals[cv] += 1

    # Get active keys (filtering out those with 0 counts if not explicit list)
    def get_keys(dim, totals):
        if isinstance(dim['keys'], str):
            return list(dim['keys'])
        # If it's a fixed list, keep it but maybe filter?
        # Usually better to show all for fixed small lists (types, rarities),
        # but for mechanics only show those present.
        if dim == DIMENSIONS['mechanic']:
            return sorted([k for k in dim['keys'] if totals[k] > 0])
        return dim['keys']

    r_keys = get_keys(r_dim, row_totals)
    c_keys = get_keys(c_dim, col_totals)

    # Output
    output_f = open(args.outfile, 'w', encoding='utf-8') if args.outfile else sys.stdout

    try:
        if args.json:
            result = {
                'row_dimension': r_dim['label'],
                'col_dimension': c_dim['label'],
                'total_cards': grand_total,
                'matrix': {str(rk): {str(ck): matrix[rk][ck] for ck in c_keys} for rk in r_keys},
                'row_totals': {str(rk): row_totals[rk] for rk in r_keys},
                'col_totals': {str(ck): col_totals[ck] for ck in c_keys}
            }
            output_f.write(json.dumps(result, indent=2) + '\n')
        elif args.csv:
            writer = csv.writer(output_f)
            header = [r_dim['label'] + ' / ' + c_dim['label']] + [str(ck) for ck in c_keys] + ['Total']
            writer.writerow(header)
            for rk in r_keys:
                row = [str(rk)] + [matrix[rk][ck] for ck in c_keys] + [row_totals[rk]]
                writer.writerow(row)
            writer.writerow(['TOTAL'] + [col_totals[ck] for ck in c_keys] + [grand_total])
        else:
            # Table Output
            r_label = r_dim['label'].upper()
            c_label = c_dim['label'].upper()
            title = f"{r_label} vs {c_label}"
            utils.print_header(title, count=grand_total, use_color=use_color, file=output_f)

            header = [r_dim['label'] + ' / ' + c_dim['label']] + [str(ck) for ck in c_keys] + ["Total"]
            if use_color:
                # Colorize column headers if it's color identity
                header_display = [utils.colorize(header[0], utils.Ansi.BOLD + utils.Ansi.UNDERLINE)]
                for ck in c_keys:
                    label = str(ck)
                    if c_dim == DIMENSIONS['color']:
                        label = utils.colorize(label, utils.Ansi.get_color_color(ck))
                    header_display.append(utils.colorize(label, utils.Ansi.BOLD + utils.Ansi.UNDERLINE))
                header_display.append(utils.colorize("Total", utils.Ansi.BOLD + utils.Ansi.UNDERLINE))
                rows = [header_display]
            else:
                rows = [header]

            for rk in r_keys:
                row_label = r_dim['formatter'](str(rk), use_color)
                row = [row_label]
                for ck in c_keys:
                    count = matrix[rk][ck]
                    row.append(datalib.color_count(count, use_color) if count > 0 else " - ")

                r_total = row_totals[rk]
                row.append(utils.colorize(str(r_total), utils.Ansi.BOLD + utils.Ansi.YELLOW) if use_color else str(r_total))
                rows.append(row)

            datalib.add_separator_row(rows)

            # Totals Row
            totals_label = "TOTAL"
            if use_color:
                totals_label = utils.colorize(totals_label, utils.Ansi.BOLD + utils.Ansi.YELLOW)

            totals_row = [totals_label]
            for ck in c_keys:
                c_total = col_totals[ck]
                totals_row.append(utils.colorize(str(c_total), utils.Ansi.BOLD + utils.Ansi.YELLOW) if use_color else str(c_total))

            totals_row.append(utils.colorize(str(grand_total), utils.Ansi.BOLD + utils.Ansi.WHITE + utils.Ansi.UNDERLINE) if use_color else str(grand_total))
            rows.append(totals_row)

            datalib.printrows(datalib.padrows(rows, aligns=['l'] + ['r'] * (len(c_keys) + 1)), indent=2, file=output_f)

    finally:
        if args.outfile:
            output_f.close()

    if not args.quiet:
        utils.print_operation_summary("Grid Analysis", grand_total, 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
