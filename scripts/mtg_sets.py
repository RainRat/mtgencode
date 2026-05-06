#!/usr/bin/env python3
import sys
import os
import json
import argparse
import re
import random
from contextlib import redirect_stdout

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import datalib
import jdecode

def load_sets(fname, verbose=False):
    if verbose:
        print(f"Loading {fname if fname != '-' else 'stdin'}...", file=sys.stderr)

    try:
        if fname == '-':
            content = json.load(sys.stdin)
        else:
            with open(fname, 'r', encoding='utf-8') as f:
                content = json.load(f)
    except Exception as e:
        print(f"Error loading {fname if fname != '-' else 'stdin'}: {e}", file=sys.stderr)
        return [], None, None

    # MTGJSON v4/v5 structure: { "data": { "SET_CODE": { ... } } }
    if 'data' not in content:
        # Fallback for files that might just be a dictionary of sets already
        if isinstance(content, dict) and any(isinstance(v, dict) and 'cards' in v for v in content.values()):
            sets_data = content
        else:
            print(f"Error: 'data' key not found in {fname}. Is this a valid MTGJSON file?", file=sys.stderr)
            return [], None, None
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

    return sets, sets_data, content

def display_sets(sets, use_color=False):
    if not sets:
        return

    utils.print_header("AVAILABLE SETS", count=len(sets), use_color=use_color)

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
    datalib.add_separator_row(rows)

    datalib.printrows(datalib.padrows(rows, aligns=['l', 'l', 'l', 'l', 'r']), indent=2)

def main():
    parser = argparse.ArgumentParser(
        description="List and filter sets in an MTGJSON file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # List all sets in a dataset
  python3 scripts/mtg_sets.py data/AllPrintings.json

  # Find sets with "Masters" in their name or code (shorthand query)
  python3 scripts/mtg_sets.py "Masters"

  # Find sets with "Masters" in their name or code (explicit flag)
  python3 scripts/mtg_sets.py data/AllPrintings.json --grep "Masters"
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Path to the MTGJSON file (e.g., AllPrintings.json). Defaults to stdin (-). '
                             'If stdin is a terminal, it attempts to use data/AllPrintings.json.')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Optional path to save the set list. If not provided, the list prints to the console.')

    # Group: Data Processing
    proc_group = parser.add_argument_group('Data Processing')
    proc_group.add_argument('-n', '--limit', type=int, default=0,
                        help='Only process the first N sets.')
    proc_group.add_argument('--shuffle', action='store_true',
                        help='Randomize the order of sets before listing.')
    proc_group.add_argument('--sample', type=int, default=0,
                        help='Pick N random sets (shorthand for --shuffle --limit N).')
    proc_group.add_argument('--sort', choices=['code', 'name', 'type', 'date', 'count'], default='date',
                        help='Sort sets by a specific criterion (Default: date).')
    proc_group.add_argument('--reverse', action='store_true', help='Reverse the sort order.')
    proc_group.add_argument('--grep', '--filter', action='append',
                        help='Only include sets matching a search pattern (checks name and code). Use multiple times for AND logic.')
    proc_group.add_argument('--summarize', action='store_true',
                        help='Show statistics and mechanical profiling for the cards in the filtered sets.')
    proc_group.add_argument('--view', action='store_true',
                        help='Display a compact list of all cards in the filtered sets.')
    proc_group.add_argument('-t', '--top', type=int, default=10,
                        help='Limit the number of entries in breakdown tables (used with --summarize).')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')

    # Color options
    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color output.')

    args = parser.parse_args()

    # UX Improvement: Smart positional argument handling
    # If the user provides an infile that doesn't exist, but it might be a search query,
    # we treat it as such and default the input to stdin/AllPrintings.json.
    if args.infile and args.infile != '-' and not os.path.exists(args.infile):
        # If there are 2 positional arguments and the first isn't a file but the second is, swap them.
        if args.outfile and os.path.exists(args.outfile):
            query = args.infile
            args.infile = args.outfile
            args.outfile = None
            if not args.grep:
                args.grep = [query]
            else:
                args.grep.append(query)
        # If only one argument was provided (or both don't exist), treat it as a query.
        else:
            if not args.grep:
                args.grep = [args.infile]
            else:
                args.grep.append(args.infile)
            args.infile = '-'

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

    # Handle --sample
    if args.sample > 0:
        args.shuffle = True
        args.limit = args.sample

    sets, sets_data, full_content = load_sets(args.infile, args.verbose)
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

    if args.shuffle:
        random.shuffle(sets)

    if args.limit > 0:
        sets = sets[:args.limit]

    output_f = sys.stdout
    if args.outfile:
        if args.verbose:
            print(f'Writing set list to: {args.outfile}', file=sys.stderr)
        output_f = open(args.outfile, 'w', encoding='utf8')

    # Determine if we should use color
    use_color = False
    if args.color is True:
        use_color = True
    elif args.color is None and output_f.isatty():
        use_color = True

    try:
        with redirect_stdout(output_f):
            display_sets(sets, use_color=use_color)

            if (args.summarize or args.view) and sets:
                set_codes = [s['code'] for s in sets]

                # Re-load cards from filtered sets
                # We wrap the data in a 'data' key if it was present in the original
                if 'data' in full_content:
                    jobj = {'data': {k: v for k, v in sets_data.items() if k in set_codes}}
                else:
                    jobj = {k: v for k, v in sets_data.items() if k in set_codes}

                allcards, _ = jdecode.mtg_open_json_obj(jobj)
                cards = jdecode._process_json_srcs(allcards, set(), verbose=args.verbose,
                                                   linetrans=True,
                                                   exclude_sets=lambda x: False,
                                                   exclude_types=lambda x: False,
                                                   exclude_layouts=lambda x: False,
                                                   report_fobj=None)

                if args.view:
                    print('\n' + (utils.colorize("CARD LIST", utils.Ansi.BOLD + utils.Ansi.CYAN + utils.Ansi.UNDERLINE) if use_color else "=== CARD LIST ==="))
                    for card in cards:
                        print(card.summary(ansi_color=use_color))

                if args.summarize:
                    print('\n' + (utils.colorize("SET SUMMARY", utils.Ansi.BOLD + utils.Ansi.CYAN + utils.Ansi.UNDERLINE) if use_color else "=== SET SUMMARY ==="))
                    mine = datalib.Datamine(cards)
                    mine.summarize(use_color=use_color, vsize=args.top)
    finally:
        if args.outfile:
            output_f.close()

if __name__ == "__main__":
    main()
