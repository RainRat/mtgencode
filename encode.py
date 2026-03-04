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
         report_file=None, quiet=False, limit=0, grep=None, sort=None, vgrep=None,
         grep_name=None, vgrep_name=None, grep_types=None, vgrep_types=None,
         grep_text=None, vgrep_text=None,
         grep_cost=None, vgrep_cost=None, grep_pt=None, vgrep_pt=None,
         grep_loyalty=None, vgrep_loyalty=None,
         sets=None, rarities=None, colors=None, cmcs=None,
         seed=None, decklist_file=None):
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
        elif sort:
             print('  Sorting cards by ' + sort + '.', file=sys.stderr)
        else:
            print('  Randomizing order of cards (seed ' + str(seed if seed is not None else 1371367) + ').', file=sys.stderr)
        if randomize_mana:
            print('  Randomizing order of symbols in manacosts.', file=sys.stderr)
        if not fmt_labeled:
            print('  NOT labeling fields for this run (may be harder to decode).', file=sys.stderr)
        if not line_transformations:
            print('  NOT using line reordering transformations', file=sys.stderr)

    if sort:
        stable = True

    cards = jdecode.mtg_open_file(fname, verbose=verbose, linetrans=line_transformations,
                                  report_file=report_file, grep=grep, vgrep=vgrep,
                                  grep_name=grep_name, vgrep_name=vgrep_name,
                                  grep_types=grep_types, vgrep_types=vgrep_types,
                                  grep_text=grep_text, vgrep_text=vgrep_text,
                                  grep_cost=grep_cost, vgrep_cost=vgrep_cost,
                                  grep_pt=grep_pt, vgrep_pt=vgrep_pt,
                                  grep_loyalty=grep_loyalty, vgrep_loyalty=vgrep_loyalty,
                                  sets=sets, rarities=rarities,
                                  colors=colors, cmcs=cmcs,
                                  shuffle=not stable, seed=seed if seed is not None else 1371367,
                                  decklist_file=decklist_file)

    if sort:
        cards = sortlib.sort_cards(cards, sort, quiet=quiet)

    if limit > 0:
        cards = cards[:limit]

    def writecards(writer):
        success_count = 0
        fail_count = 0
        for card in tqdm(cards, disable=quiet or len(cards) < 5, desc="Encoding"):
            try:
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
                success_count += 1
            except Exception:
                fail_count += 1
        return success_count, fail_count

    total_success = 0
    total_fail = 0
    if oname:
        if verbose:
            print(utils.colorize('Writing output to: ', utils.Ansi.BOLD + utils.Ansi.CYAN) + oname, file=sys.stderr)
        with open(oname, 'w', encoding='utf8') as ofile:
            s, f = writecards(ofile)
            total_success += s
            total_fail += f
    else:
        s, f = writecards(sys.stdout)
        total_success += s
        total_fail += f
        sys.stdout.flush()

    # Provide clear feedback on operation completion
    utils.print_operation_summary("Encoding", total_success, total_fail, quiet=quiet)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Convert Magic: The Gathering card data into text for AI training.")
    
    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (MTGJSON or Scryfall JSON, JSONL, CSV, MSE, ZIP, or MTG Decklist), an encoded file, or a directory. Defaults to stdin (-).')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save the output. If not provided, output prints to the console.')

    # Group: Encoding Options
    enc_group = parser.add_argument_group('Encoding Options')
    enc_group.add_argument('-e', '--encoding', default='std', choices=utils.formats,
                        help="The encoding format to use: 'std' (Name last, default), 'named' (Name first), "
                             "'noname' (No names), 'rfields' (Random field order), "
                             "'old' (Legacy), 'norarity' (No rarity), 'vec' (Numerical vectors), "
                             "or 'custom' (User-defined).",
    )
    enc_group.add_argument('--nolabel', action='store_true',
                        help="Remove field labels (like '|cost|' or '|text|') from the output.")
    enc_group.add_argument('--nolinetrans', action='store_true',
                        help='Keep the original order of card text lines (disable automatic reordering).')

    # Group: Data Processing
    proc_group = parser.add_argument_group('Data Processing')
    proc_group.add_argument('-r', '--randomize', action='store_true',
                        help='Randomize the order of mana symbols (e.g., {W}{U} vs {U}{W}) to help the AI learn better.')
    proc_group.add_argument('-n', '--limit', type=int, default=0,
                        help='Only process the first N cards.')
    proc_group.add_argument('-s', '--stable', action='store_true',
                        help='Keep the original order of cards from the input (do not shuffle).')
    proc_group.add_argument('--seed', type=int,
                        help='Seed for the random number generator (Default: 1371367).')
    proc_group.add_argument('--sample', type=int, default=0,
                        help='Pick N random cards from the input (shorthand for --limit N). Shuffling is enabled unless --stable is used.')
    proc_group.add_argument('--sort', choices=['name', 'color', 'type', 'cmc'],
                        help='Sort cards by a specific criterion (enables --stable).')
    proc_group.add_argument('--grep', action='append',
                        help='Only include cards matching a search pattern (checks name, type, and text). Use multiple times for AND logic.')
    proc_group.add_argument('--grep-name', action='append',
                        help='Only include cards whose name matches a search pattern.')
    proc_group.add_argument('--grep-type', action='append',
                        help='Only include cards whose typeline matches a search pattern.')
    proc_group.add_argument('--grep-text', action='append',
                        help='Only include cards whose rules text matches a search pattern.')
    proc_group.add_argument('--grep-cost', action='append',
                        help='Only include cards whose mana cost matches a search pattern.')
    proc_group.add_argument('--grep-pt', action='append',
                        help='Only include cards whose power/toughness matches a search pattern.')
    proc_group.add_argument('--grep-loyalty', action='append',
                        help='Only include cards whose loyalty/defense matches a search pattern.')
    proc_group.add_argument('--vgrep', '--exclude', action='append',
                        help='Exclude cards matching a search pattern (checks name, type, and text). Use multiple times for OR logic.')
    proc_group.add_argument('--exclude-name', action='append',
                        help='Exclude cards whose name matches a search pattern.')
    proc_group.add_argument('--exclude-type', action='append',
                        help='Exclude cards whose typeline matches a search pattern.')
    proc_group.add_argument('--exclude-text', action='append',
                        help='Exclude cards whose rules text matches a search pattern.')
    proc_group.add_argument('--exclude-cost', action='append',
                        help='Exclude cards whose mana cost matches a search pattern.')
    proc_group.add_argument('--exclude-pt', action='append',
                        help='Exclude cards whose power/toughness matches a search pattern.')
    proc_group.add_argument('--exclude-loyalty', action='append',
                        help='Exclude cards whose loyalty/defense matches a search pattern.')
    proc_group.add_argument('--set', action='append',
                        help='Only include cards from specific sets (e.g., MOM, MRD). Supports multiple sets (OR logic).')
    proc_group.add_argument('--rarity', action='append',
                        help="Only include cards of specific rarities. Supports full names (e.g., 'common', 'mythic') or shorthands: O (Common), N (Uncommon), A (Rare), Y (Mythic), I (Special), L (Basic Land). Supports multiple rarities (OR logic).")
    proc_group.add_argument('--colors', action='append',
                        help="Only include cards of specific colors (W, U, B, R, G). Use 'C' or 'A' for colorless. Supports multiple colors (OR logic).")
    proc_group.add_argument('--cmc', action='append',
                        help='Only include cards with specific CMC (Converted Mana Cost) values. Supports multiple values (OR logic).')
    proc_group.add_argument('--deck-filter', '--decklist-filter', dest='deck',
                        help='Filter cards using a standard MTG decklist file. Also multiplies cards in the output based on their counts in the decklist.')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true',
                        help='Enable detailed status messages.')
    debug_group.add_argument('-q', '--quiet', action='store_true',
                        help='Suppress the progress bar.')
    debug_group.add_argument('--report-unparsed',
                        help='File path to save the raw data of cards that failed to parse (useful for debugging).')

    args = parser.parse_args()

    # Handle --sample
    if args.sample > 0:
        args.limit = args.sample

    main(args.infile, args.outfile, verbose = args.verbose, encoding = args.encoding,
         nolinetrans = args.nolinetrans, randomize = args.randomize, nolabel = args.nolabel,
         stable = args.stable, report_file = args.report_unparsed, quiet=args.quiet,
         limit=args.limit, grep=args.grep, sort=args.sort, vgrep=args.vgrep,
         grep_name=args.grep_name, vgrep_name=args.exclude_name,
         grep_types=args.grep_type, vgrep_types=args.exclude_type,
         grep_text=args.grep_text, vgrep_text=args.exclude_text,
         grep_cost=args.grep_cost, vgrep_cost=args.exclude_cost,
         grep_pt=args.grep_pt, vgrep_pt=args.exclude_pt,
         grep_loyalty=args.grep_loyalty, vgrep_loyalty=args.exclude_loyalty,
         sets=args.set, rarities=args.rarity, colors=args.colors, cmcs=args.cmc,
         seed=args.seed, decklist_file=args.deck)
    exit(0)
