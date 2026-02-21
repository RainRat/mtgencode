#!/usr/bin/env python3
import sys
import os
import argparse
import json
from contextlib import redirect_stdout

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
from datalib import Datamine

# Try to import tqdm for progress bars
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

def main(fname, verbose = True, outliers = False, dump_all = False, grep = None, use_color = None, limit = 0, json_out = False, vgrep = None, shuffle = False, seed = None, quiet = False, oname = None):

    # Set default format to JSON if no specific output format is selected and outfile is .json
    if not json_out and oname and oname.endswith('.json'):
        json_out = True

    # Use the robust mtg_open_file for all loading and filtering.
    # We disable default exclusions to match original summarize.py behavior.
    cards = jdecode.mtg_open_file(fname, verbose=verbose, grep=grep, vgrep=vgrep,
                                  exclude_sets=lambda x: False,
                                  exclude_types=lambda x: False,
                                  exclude_layouts=lambda x: False,
                                  shuffle=shuffle, seed=seed)

    if limit > 0:
        cards = cards[:limit]

    card_srcs = []
    for card in tqdm(cards, disable=quiet, desc="Analyzing cards", unit="card"):
        if card.json:
            card_srcs.append(card.json)
        else:
            card_srcs.append(card.raw if card.raw else card.encode())

    mine = Datamine(card_srcs)

    # Determine if we should use color
    actual_use_color = False
    if use_color is True:
        actual_use_color = True
    elif use_color is None and not oname and sys.stdout.isatty():
        actual_use_color = True

    output_f = sys.stdout
    if oname:
        if verbose:
            print(f'Writing {"JSON " if json_out else ""}summary to: {oname}', file=sys.stderr)
        output_f = open(oname, 'w', encoding='utf8')

    try:
        if json_out:
            output_f.write(json.dumps(mine.to_dict(), indent=2) + '\n')
        else:
            with redirect_stdout(output_f):
                mine.summarize(use_color=actual_use_color)
                if outliers or dump_all:
                    mine.outliers(dump_invalid = dump_all, use_color=actual_use_color)
    finally:
        if oname:
            output_f.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Summarizes Magic: The Gathering card datasets.")
    
    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, JSONL, CSV, MSE, or ZIP), an encoded file, or a directory. Defaults to stdin (-).')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save the summary output. If not provided, output prints to the console. The format is automatically detected from the file extension (.json for JSON, otherwise text).')
    io_group.add_argument('--json', action='store_true',
                        help='Output statistics in JSON format (Auto-detected for .json).')

    # Group: Processing Options
    proc_group = parser.add_argument_group('Processing Options')
    proc_group.add_argument('-x', '--outliers', action='store_true',
                        help='Show extra details and unusual cards.')
    proc_group.add_argument('-a', '--all', action='store_true',
                        help='Show all information and dump invalid cards.')
    proc_group.add_argument('-n', '--limit', type=int, default=0,
                        help='Only process the first N cards.')
    proc_group.add_argument('--shuffle', action='store_true',
                        help='Randomize the order of cards before summarizing.')
    proc_group.add_argument('--seed', type=int,
                        help='Seed for the random number generator.')
    proc_group.add_argument('--sample', type=int, default=0,
                        help='Pick N random cards from the input (shorthand for --shuffle --limit N).')
    proc_group.add_argument('--grep', action='append',
                        help='Only include cards that match a regex (matches name, type, or text). Use multiple times for AND logic.')
    proc_group.add_argument('--vgrep', '--exclude', action='append',
                        help='Exclude cards that match a regex (matches name, type, or text). Use multiple times for OR logic.')
    
    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output.')
    debug_group.add_argument('-q', '--quiet', action='store_true',
                        help='Suppress the progress bar.')

    # Color options
    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None,
                        help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color',
                        help='Disable ANSI color output.')

    args = parser.parse_args()

    # Handle --sample
    if args.sample > 0:
        args.shuffle = True
        args.limit = args.sample

    main(args.infile, verbose = args.verbose, outliers = args.outliers, dump_all = args.all, grep = args.grep, use_color = args.color, limit = args.limit, json_out = args.json, vgrep = args.vgrep, shuffle = args.shuffle, seed = args.seed, quiet = args.quiet, oname = args.outfile)
    exit(0)
