#!/usr/bin/env python3
import sys
import os
import argparse
import json

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)
import utils
import jdecode
from datalib import Datamine

def main(fname, verbose = True, outliers = False, dump_all = False, grep = None, use_color = False, limit = 0, json_out = False):
    # Use the robust mtg_open_file for all loading and filtering.
    # We disable default exclusions to match original summarize.py behavior.
    cards = jdecode.mtg_open_file(fname, verbose=verbose, grep=grep,
                                  exclude_sets=lambda x: False,
                                  exclude_types=lambda x: False,
                                  exclude_layouts=lambda x: False)

    if limit > 0:
        cards = cards[:limit]

    card_srcs = []
    for card in cards:
        if card.json:
            card_srcs.append(card.json)
        else:
            card_srcs.append(card.raw if card.raw else card.encode())

    mine = Datamine(card_srcs)
    if json_out:
        print(json.dumps(mine.to_dict(), indent=2))
    else:
        mine.summarize(use_color=use_color)
        if outliers or dump_all:
            mine.outliers(dump_invalid = dump_all, use_color=use_color)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Summarizes Magic: The Gathering card datasets.")
    
    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='encoded card file or JSON/JSONL corpus to process. Defaults to stdin (-).')
    io_group.add_argument('--json', action='store_true',
                        help='Output statistics in JSON format.')

    # Group: Processing Options
    proc_group = parser.add_argument_group('Processing Options')
    proc_group.add_argument('-x', '--outliers', action='store_true',
                        help='show additional diagnostics and edge cases')
    proc_group.add_argument('-a', '--all', action='store_true',
                        help='show all information and dump invalid cards')
    proc_group.add_argument('-n', '--limit', type=int, default=0,
                        help='Limit the number of cards to process.')
    proc_group.add_argument('--grep', action='append',
                        help='Filter cards by regex (matches name, type, or text). Can be used multiple times (AND logic).')
    
    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true',
                        help='verbose output')

    # Color options
    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None,
                        help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color',
                        help='Disable ANSI color output.')

    args = parser.parse_args()

    # Determine if we should use color
    use_color = False
    if args.color is True:
        use_color = True
    elif args.color is None and sys.stdout.isatty():
        use_color = True

    main(args.infile, verbose = args.verbose, outliers = args.outliers, dump_all = args.all, grep = args.grep, use_color = use_color, limit = args.limit, json_out = args.json)
    exit(0)
