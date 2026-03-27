#!/usr/bin/env python3
import sys
import os
import json
import argparse
import re

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import datalib

def load_sets(fname, verbose=False):
    if verbose:
        print(f"Loading {fname}...", file=sys.stderr)

    try:
        with open(fname, 'r', encoding='utf-8') as f:
            content = json.load(f)
    except Exception as e:
        print(f"Error loading {fname}: {e}", file=sys.stderr)
        return []

    # MTGJSON v4/v5 structure: { "data": { "SET_CODE": { ... } } }
    if 'data' not in content:
        # Fallback for files that might just be a dictionary of sets already
        if isinstance(content, dict) and any('cards' in v for v in content.values()):
            sets_data = content
        else:
            print(f"Error: 'data' key not found in {fname}. Is this a valid MTGJSON file?", file=sys.stderr)
            return []
    else:
        sets_data = content['data']

    sets = []

    for code, data in sets_data.items():
        sets.append({
            'code': data.get('code', code),
            'name': data.get('name', 'Unknown'),
            'type': data.get('type', 'Unknown'),
            'releaseDate': data.get('releaseDate', '0000-00-00'),
            'count': len(data.get('cards', []))
        })

    return sets

def display_sets(sets, use_color=False):
    if not sets:
        return

    header = ["Code", "Name", "Type", "Release Date", "Count"]
    if use_color:
        header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

    # Pre-formatting for table data
    rows = [header]

    for s in sets:
        code = s['code']
        name = s['name']
        stype = s['type']
        date = s['releaseDate']
        count = str(s['count'])

        if use_color:
            code = utils.colorize(code, utils.Ansi.BOLD + utils.Ansi.CYAN)
            name = utils.colorize(name, utils.Ansi.BOLD)
            # Use different colors for different set types
            if stype.lower() in ['core', 'expansion']:
                stype = utils.colorize(stype, utils.Ansi.BOLD + utils.Ansi.GREEN)
            elif stype.lower() in ['funny', 'memorabilia', 'alchemy']:
                stype = utils.colorize(stype, utils.Ansi.BOLD + utils.Ansi.RED)
            else:
                stype = utils.colorize(stype, utils.Ansi.BOLD + utils.Ansi.YELLOW)

            count = utils.colorize(count, utils.Ansi.BOLD + utils.Ansi.GREEN)

        rows.append([code, name, stype, date, count])

    # Get column widths and add a separator
    col_widths = datalib.get_col_widths(rows)
    separator = ['-' * w for w in col_widths]
    rows.insert(1, separator)

    datalib.printrows(datalib.padrows(rows, aligns=['l', 'l', 'l', 'l', 'r']))

def main():
    parser = argparse.ArgumentParser(description="List and filter sets in an MTGJSON file.")

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', help='Path to the MTGJSON file (e.g., AllPrintings.json)')

    # Group: Data Processing
    proc_group = parser.add_argument_group('Data Processing')
    proc_group.add_argument('--sort', choices=['code', 'name', 'type', 'date', 'count'], default='date',
                        help='Sort sets by a specific criterion (Default: date).')
    proc_group.add_argument('--reverse', action='store_true', help='Reverse the sort order.')
    proc_group.add_argument('--grep', '--filter', action='append',
                        help='Only include sets matching a search pattern (checks name and code). Use multiple times for AND logic.')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')

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

    sets = load_sets(args.infile, args.verbose)
    if not sets:
        sys.exit(1)

    # Filtering
    if args.grep:
        greps = [re.compile(p, re.IGNORECASE) for p in args.grep]
        filtered_sets = []
        for s in sets:
            match = True
            for pattern in greps:
                if not (pattern.search(s['name']) or pattern.search(s['code'])):
                    match = False
                    break
            if match:
                filtered_sets.append(s)
        sets = filtered_sets

    # Sorting
    sort_key_map = {
        'code': lambda x: x['code'].lower(),
        'name': lambda x: x['name'].lower(),
        'type': lambda x: x['type'].lower(),
        'date': lambda x: x['releaseDate'],
        'count': lambda x: x['count']
    }

    sets.sort(key=sort_key_map[args.sort], reverse=args.reverse)

    display_sets(sets, use_color=use_color)
    print(f"\nFound {len(sets)} sets matching criteria.")

if __name__ == "__main__":
    main()
