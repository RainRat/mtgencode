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
from tqdm import tqdm

def main(fname, oname = None, verbose = True, encoding = 'std',
         nolinetrans = False, randomize = False, nolabel = False, stable = False,
         report_file=None, quiet=False):
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
        print('Preparing to encode:')
        print('  Using encoding ' + repr(encoding))
        if stable:
            print('  NOT randomizing order of cards.')
        if randomize_mana:
            print('  Randomizing order of symbols in manacosts.')
        if not fmt_labeled:
            print('  NOT labeling fields for this run (may be harder to decode).')
        if not line_transformations:
            print('  NOT using line reordering transformations')

    cards = jdecode.mtg_open_file(fname, verbose=verbose, linetrans=line_transformations, report_file=report_file)

    # This should give a random but consistent ordering, to make comparing changes
    # between the output of different versions easier.
    if not stable:
        random.seed(1371367)
        random.shuffle(cards)

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
            print('Writing output to: ' + oname)
        with open(oname, 'w', encoding='utf8') as ofile:
            writecards(ofile)
    else:
        writecards(sys.stdout)
        sys.stdout.flush()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    
    parser.add_argument('infile', 
                        help='Input JSON file containing card data (e.g., AllPrintings.json) or an already encoded file.')
    parser.add_argument('outfile', nargs='?', default=None,
                        help='Path to save the output. If not provided, output prints to the console (stdout).')
    parser.add_argument('-e', '--encoding', default='std', choices=utils.formats,
                        help="Format for the output data. 'std' (default) puts the name last. 'named' puts the name first. 'vec' produces a vectorized format for training.",
    )
    parser.add_argument('-r', '--randomize', action='store_true',
                        help='Shuffle mana symbols (e.g., {W}{U} vs {U}{W}) for data augmentation.')
    parser.add_argument('--nolinetrans', action='store_true',
                        help='Disable automatic reordering of card text lines (keep original order).')
    parser.add_argument('--nolabel', action='store_true',
                        help="Remove field labels (e.g., '|cost|') from the output.")
    parser.add_argument('-s', '--stable', action='store_true',
                        help='Preserve the original order of cards from the input file (do not shuffle).')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output.')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Suppress the progress bar.')
    parser.add_argument('--report-unparsed',
                        help='File path to save raw JSON of cards that failed to parse (useful for debugging).')

    args = parser.parse_args()
    main(args.infile, args.outfile, verbose = args.verbose, encoding = args.encoding,
         nolinetrans = args.nolinetrans, randomize = args.randomize, nolabel = args.nolabel,
         stable = args.stable, report_file = args.report_unparsed, quiet=args.quiet)
    exit(0)
