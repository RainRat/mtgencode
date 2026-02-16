#!/usr/bin/env python3
import sys
import os

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
sys.path.append(libdir)
import re
import random
import utils
import jdecode
import cardlib
import sortlib
from tqdm import tqdm

def main(fname, oname = None, verbose = True, encoding = 'std',
         nolinetrans = False, randomize = False, nolabel = False, stable = False,
         report_file=None, quiet=False, limit=0, grep=None, sort=None):
    fmt_ordered = cardlib.fmt_ordered_default
    fmt_labeled = None if nolabel else cardlib.fmt_labeled_default
    fieldsep = utils.fieldsep
    line_transformations = not nolinetrans
    randomize_fields = False
    randomize_mana = randomize
    initial_sep = True
    final_sep = True

    # set the properties of the encoding
    ENCODING_CONFIG = {
        'std': {},
        'named': {'fmt_ordered': cardlib.fmt_ordered_named},
        'noname': {'fmt_ordered': cardlib.fmt_ordered_noname},
        'rfields': {'randomize_fields': True, 'final_sep': False},
        'old': {'fmt_ordered': cardlib.fmt_ordered_old},
        'norarity': {'fmt_ordered': cardlib.fmt_ordered_norarity},
        'vec': {},
        'custom': {},
    }

    config = ENCODING_CONFIG.get(encoding)
    if config is None:
        raise ValueError('encode.py: unknown encoding: ' + encoding)

    fmt_ordered = config.get('fmt_ordered', fmt_ordered)
    randomize_fields = config.get('randomize_fields', randomize_fields)
    final_sep = config.get('final_sep', final_sep)

    if verbose:
        print(utils.colorize('Preparing to encode:', utils.Ansi.BOLD + utils.Ansi.CYAN), file=sys.stderr)
        print('  Using encoding ' + repr(encoding), file=sys.stderr)
        if stable:
            print('  NOT randomizing order of cards.', file=sys.stderr)
        if randomize_mana:
            print('  Randomizing order of symbols in manacosts.', file=sys.stderr)
        if not fmt_labeled:
            print('  NOT labeling fields for this run (may be harder to decode).', file=sys.stderr)
        if not line_transformations:
            print('  NOT using line reordering transformations', file=sys.stderr)

    cards = jdecode.mtg_open_file(fname, verbose=verbose, linetrans=line_transformations, report_file=report_file, grep=grep)

    if sort:
        cards = sortlib.sort_cards(cards, sort, quiet=quiet)
        stable = True

    # This should give a random but consistent ordering, to make comparing changes
    # between the output of different versions easier.
    if not stable:
        random.seed(1371367)
        random.shuffle(cards)

    if limit > 0:
        cards = cards[:limit]

    def writecards(writer):
        for card in tqdm(cards, disable=quiet):
            if encoding in ['vec']:
                writer.write(card.vectorize() + '\n\n')
            else:
                writer.write(card.encode(fmt_ordered = fmt_ordered,
                                         fmt_labeled = fmt_labeled,
                                         fieldsep = fieldsep,
                                         randomize_fields = randomize_fields,
                                         randomize_mana = randomize_mana,
                                         initial_sep = initial_sep,
                                         final_sep = final_sep) 
                             + utils.cardsep)

    if oname:
        if verbose:
            print(utils.colorize('Writing output to: ', utils.Ansi.BOLD + utils.Ansi.CYAN) + oname, file=sys.stderr)
        with open(oname, 'w', encoding='utf8') as ofile:
            writecards(ofile)
    else:
        writecards(sys.stdout)
        sys.stdout.flush()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Encodes Magic: The Gathering card data into text formats for AI training.")
    
    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input JSON file containing card data (e.g., AllPrintings.json), a CSV/JSONL file, or an already encoded file. Defaults to stdin (-).')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save the output. If not provided, output prints to the console (stdout).')

    # Group: Encoding Options
    enc_group = parser.add_argument_group('Encoding Options')
    enc_group.add_argument('-e', '--encoding', default='std', choices=utils.formats,
                        help="Card data format: 'std' (name last, default), 'named' (name first), "
                             "'noname' (no name), 'rfields' (random field order), "
                             "'old' (legacy), 'norarity' (no rarity), 'vec' (vectorized), "
                             "or 'custom' (user-defined).",
    )
    enc_group.add_argument('--nolabel', action='store_true',
                        help="Remove field labels (e.g., '|cost|') from the output.")
    enc_group.add_argument('--nolinetrans', action='store_true',
                        help='Disable automatic reordering of card text lines (keep original order).')

    # Group: Data Processing
    proc_group = parser.add_argument_group('Data Processing')
    proc_group.add_argument('-r', '--randomize', action='store_true',
                        help='Shuffle mana symbols (e.g., {W}{U} vs {U}{W}) for data augmentation.')
    proc_group.add_argument('-n', '--limit', type=int, default=0,
                        help='Limit the number of cards to encode.')
    proc_group.add_argument('-s', '--stable', action='store_true',
                        help='Preserve the original order of cards from the input file (do not shuffle).')
    proc_group.add_argument('--sort', choices=['name', 'color', 'type', 'cmc'],
                        help='Sort cards by the specified criterion.')
    proc_group.add_argument('--grep', action='append',
                        help='Filter cards by regex (matches name, type, or text). Can be used multiple times (AND logic).')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output.')
    debug_group.add_argument('-q', '--quiet', action='store_true',
                        help='Suppress the progress bar.')
    debug_group.add_argument('--report-unparsed',
                        help='File path to save raw JSON of cards that failed to parse (useful for debugging).')

    args = parser.parse_args()
    main(args.infile, args.outfile, verbose = args.verbose, encoding = args.encoding,
         nolinetrans = args.nolinetrans, randomize = args.randomize, nolabel = args.nolabel,
         stable = args.stable, report_file = args.report_unparsed, quiet=args.quiet,
         limit=args.limit, grep=args.grep, sort=args.sort)
    exit(0)
