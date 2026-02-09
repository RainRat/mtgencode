#!/usr/bin/env python3
import sys
import os

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)
import utils
import jdecode
from datalib import Datamine

def main(fname, verbose = True, outliers = False, dump_all = False, grep = None):
    """
    Loads card data from a file or directory and prints a statistical summary.

    Args:
        fname (str): Path to the input file (encoded text, JSON, or CSV) or directory.
                     Use '-' for standard input.
        verbose (bool): If True, prints additional loading diagnostics to stderr.
        outliers (bool): If True, includes extra information about unusual cards (e.g., longest names).
        dump_all (bool): If True, prints the raw data for all invalid or unparsed cards.
        grep (list of str): A list of regex patterns to filter cards before analysis.
    """
    # Use the robust mtg_open_file for all loading and filtering.
    # We disable default exclusions to match original summarize.py behavior.
    cards = jdecode.mtg_open_file(fname, verbose=verbose, grep=grep,
                                  exclude_sets=lambda x: False,
                                  exclude_types=lambda x: False,
                                  exclude_layouts=lambda x: False)

    card_srcs = []
    for card in cards:
        if card.json:
            card_srcs.append(card.json)
        else:
            card_srcs.append(card.raw if card.raw else card.encode())

    mine = Datamine(card_srcs)
    mine.summarize()
    if outliers or dump_all:
        mine.outliers(dump_invalid = dump_all)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Summarizes Magic card data, providing statistics on colors, types, and other attributes.")

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Path to the card data file (encoded text, JSON, or CSV) or a directory. Defaults to stdin (-).')

    # Group: Processing Options
    proc_group = parser.add_argument_group('Processing Options')
    proc_group.add_argument('-x', '--outliers', action='store_true',
                        help='Include additional diagnostics and edge cases in the summary.')
    proc_group.add_argument('-a', '--all', action='store_true',
                        help='Show all available information and dump the contents of invalid cards.')
    proc_group.add_argument('--grep', action='append',
                        help='Filter cards by regex (matches name, type, or rules text). Can be used multiple times (AND logic).')
    
    # Group: Logging & Debugging
    log_group = parser.add_argument_group('Logging & Debugging')
    log_group.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output, including loading diagnostics.')
    
    args = parser.parse_args()
    main(args.infile, verbose = args.verbose, outliers = args.outliers, dump_all = args.all, grep = args.grep)
    exit(0)
