#!/usr/bin/env python3
import sys
import os

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)
import utils
import jdecode
from datalib import Datamine

def main(fname, verbose = True, outliers = False, dump_all = False, grep = None):
    # Use the robust mtg_open_file for all loading and filtering.
    # We disable default exclusions to match original summarize.py behavior.
    cards = jdecode.mtg_open_file(fname, verbose=verbose, grep=grep,
                                  exclude_sets=lambda x: False,
                                  exclude_types=lambda x: False,
                                  exclude_layouts=lambda x: False)
    # Datamine expects card_srcs (strings) or Card objects?
    # Let's check datalib.py again.

    # Actually, Datamine.__init__ does:
    # for card_src in card_srcs:
    #     card = Card(card_src)
    # But it also works if card_src IS a Card object?
    # Wait, Card(card_object) might fail?

    # If I pass Card objects to Datamine, it might re-parse them if I'm not careful.
    # Let's check cardlib.py Card constructor again.

    # In Card.__init__(self, src, ...):
    # if isinstance(src, dict): ...
    # else: self.raw = src ...

    # If I pass a Card object, it will be treated as "else" and it might fail.
    # So I should pass the raw strings or dicts.

    # Actually, I can just pass the list of Cards and update Datamine to handle it.
    # But it's easier to just pass card.raw or card.json.

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
    parser = argparse.ArgumentParser()
    
    parser.add_argument('infile', 
                        help='encoded card file or json corpus to process')
    parser.add_argument('-x', '--outliers', action='store_true',
                        help='show additional diagnostics and edge cases')
    parser.add_argument('-a', '--all', action='store_true',
                        help='show all information and dump invalid cards')
    parser.add_argument('-v', '--verbose', action='store_true', 
                        help='verbose output')
    parser.add_argument('--grep', action='append',
                        help='Filter cards by regex (matches name, type, or text). Can be used multiple times (AND logic).')
    
    args = parser.parse_args()
    main(args.infile, verbose = args.verbose, outliers = args.outliers, dump_all = args.all, grep = args.grep)
    exit(0)
