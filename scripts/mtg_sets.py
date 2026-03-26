#!/usr/bin/env python3
import sys
import os
import json
import argparse
from collections import OrderedDict

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import datalib

def get_set_type_color(set_type):
    """Returns an ANSI color code based on the set type."""
    st = set_type.lower()
    if st in ['core', 'starter']:
        return utils.Ansi.GREEN
    if st in ['expansion', 'masters']:
        return utils.Ansi.CYAN
    if st in ['funny', 'memorabilia', 'token']:
        return utils.Ansi.RED
    if st in ['commander', 'duel_deck', 'planechase', 'archenemy']:
        return utils.Ansi.YELLOW
    if st in ['promo', 'box', 'vanguard']:
        return utils.Ansi.MAGENTA
    return utils.Ansi.BOLD

def main():
    parser = argparse.ArgumentParser(
        description="List and explore Magic: The Gathering sets within a JSON dataset (MTGJSON format).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Example:\n  python3 scripts/mtg_sets.py data/AllPrintings.json --sort date --grep Ravnica"
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='data/AllPrintings.json',
                        help='Input card data (MTGJSON format). Defaults to data/AllPrintings.json.')

    # Group: Filtering & Sorting
    proc_group = parser.add_argument_group('Filtering & Sorting')
    proc_group.add_argument('--grep', help='Filter sets by name or code (case-insensitive).')
    proc_group.add_argument('--sort', choices=['code', 'name', 'type', 'date', 'count'], default='date',
                        help='Sort the set list by a specific column. Default: date.')
    proc_group.add_argument('--reverse', action='store_true', help='Reverse the sort order.')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    debug_group.add_argument('-q', '--quiet', action='store_true', help='Suppress the progress bar and summary.')

    # Color options
    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color output.')

    args = parser.parse_args()

    # Determine if we should use color
    use_color = False
    if args.color is True:
        use_color = True
    elif args.color is None and sys.stdout.isatty():
        use_color = True

    if not os.path.exists(args.infile):
        print(f"Error: File not found: {args.infile}", file=sys.stderr)
        sys.exit(1)

    if args.verbose:
        print(f"Loading {args.infile}...", file=sys.stderr)

    try:
        with open(args.infile, 'r', encoding='utf8') as f:
            jobj = json.load(f)
    except Exception as e:
        print(f"Error reading JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # Handle MTGJSON v4/v5 structure
    if 'data' in jobj:
        set_data_dict = jobj['data']
    else:
        # If it's just a dict of sets without the 'data' wrapper
        set_data_dict = jobj

    sets = []
    for code, data in set_data_dict.items():
        if not isinstance(data, dict):
            continue

        name = data.get('name', 'Unknown')
        set_type = data.get('type', 'Unknown')
        release_date = data.get('releaseDate', '0000-00-00')
        card_count = len(data.get('cards', []))

        # Filtering
        if args.grep:
            search_str = f"{code} {name}".lower()
            if args.grep.lower() not in search_str:
                continue

        sets.append({
            'code': code,
            'name': name,
            'type': set_type,
            'date': release_date,
            'count': card_count
        })

    if not sets:
        if not args.quiet:
            print("No sets found matching the criteria.", file=sys.stderr)
        return

    # Sorting
    if args.sort == 'code':
        sets.sort(key=lambda x: x['code'], reverse=args.reverse)
    elif args.sort == 'name':
        sets.sort(key=lambda x: x['name'], reverse=args.reverse)
    elif args.sort == 'type':
        sets.sort(key=lambda x: (x['type'], x['date']), reverse=args.reverse)
    elif args.sort == 'date':
        sets.sort(key=lambda x: x['date'], reverse=not args.reverse) # Newest first by default
    elif args.sort == 'count':
        sets.sort(key=lambda x: x['count'], reverse=not args.reverse)

    # Table Generation
    header = ["Code", "Name", "Type", "Release Date", "Cards"]
    rows = []

    if use_color:
        rows.append([utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header])
    else:
        rows.append(header)

    for s in sets:
        code_str = s['code']
        name_str = s['name']
        type_str = s['type']
        date_str = s['date']
        count_str = str(s['count'])

        if use_color:
            color = get_set_type_color(s['type'])
            code_str = utils.colorize(code_str, utils.Ansi.BOLD + color)
            type_str = utils.colorize(type_str, color)
            count_str = utils.colorize(count_str, utils.Ansi.GREEN)

        rows.append([code_str, name_str, type_str, date_str, count_str])

    # Print Table
    if not args.quiet:
        title = f"SET LIST: {args.infile}"
        if use_color:
            title = utils.colorize(title, utils.Ansi.BOLD + utils.Ansi.CYAN)
        print(title)

    for row in datalib.padrows(rows, aligns=['l', 'l', 'l', 'l', 'r']):
        print(row)

    if not args.quiet:
        utils.print_operation_summary("Set Indexing", len(sets), 0, quiet=args.quiet)

if __name__ == '__main__':
    main()
