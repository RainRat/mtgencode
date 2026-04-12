#!/usr/bin/env python3
import sys
import os
import argparse
import json
from contextlib import redirect_stdout

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import cardlib
import jdecode
import sortlib
from datalib import Datamine

# Try to import tqdm for progress bars
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

def main(fname, verbose = True, outliers = False, dump_all = False,
         nolinetrans = False, nolabel = False,
         grep = None, use_color = None, limit = 0, json_out = False, vgrep = None,
         grep_name=None, vgrep_name=None, grep_types=None, vgrep_types=None,
         grep_text=None, vgrep_text=None,
         grep_cost=None, vgrep_cost=None, grep_pt=None, vgrep_pt=None,
         grep_loyalty=None, vgrep_loyalty=None,
         sets = None, rarities = None, colors=None, cmcs=None,
         pows=None, tous=None, loys=None,
         mechanics=None,
         identities=None, id_counts=None,
         shuffle = False, seed = None, quiet = False, oname = None, decklist_file = None,
         top = 10, booster = 0, sort = None, box = 0):

    # Set default format to JSON if no specific output format is selected and outfile is .json
    if not json_out and oname and oname.endswith('.json'):
        json_out = True

    # Use the robust mtg_open_file for all loading and filtering.
    # We disable default exclusions to match original summarize.py behavior.
    search_stats = {}
    cards = jdecode.mtg_open_file(fname, verbose=verbose, linetrans=not nolinetrans,
                                  fmt_labeled=None if nolabel else cardlib.fmt_labeled_default,
                                  grep=grep, vgrep=vgrep,
                                  grep_name=grep_name, vgrep_name=vgrep_name,
                                  grep_types=grep_types, vgrep_types=vgrep_types,
                                  grep_text=grep_text, vgrep_text=vgrep_text,
                                  grep_cost=grep_cost, vgrep_cost=vgrep_cost,
                                  grep_pt=grep_pt, vgrep_pt=vgrep_pt,
                                  grep_loyalty=grep_loyalty, vgrep_loyalty=vgrep_loyalty,
                                  sets=sets, rarities=rarities,
                                  colors=colors, cmcs=cmcs,
                                  pows=pows, tous=tous, loys=loys,
                                  mechanics=mechanics,
                                  identities=identities, id_counts=id_counts,
                                  exclude_sets=lambda x: False,
                                  exclude_types=lambda x: False,
                                  exclude_layouts=lambda x: False,
                                  shuffle=shuffle, seed=seed,
                                  decklist_file=decklist_file,
                                  stats=search_stats,
                                  booster=booster,
                                  box=box)

    if sort:
        cards = sortlib.sort_cards(cards, sort, quiet=quiet)

    if limit > 0:
        cards = cards[:limit]

    mine = Datamine(cards, search_stats=search_stats)

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
                mine.summarize(use_color=actual_use_color, vsize=top)
                if outliers or dump_all:
                    mine.outliers(dump_invalid = dump_all, use_color=actual_use_color, vsize=top)
    finally:
        if oname:
            output_f.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Show statistics, design budget analysis, mechanical profiling, and details about a Magic: The Gathering card dataset.")
    
    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (MTGJSON or Scryfall JSON, JSONL, CSV, MSE, XML, ZIP, or MTG Decklist), an encoded file, or a directory. Defaults to stdin (-).')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save the summary output. If not provided, output prints to the console. The format is automatically detected from the file extension (.json for JSON, otherwise text).')
    io_group.add_argument('-j', '--json', action='store_true',
                        help='Output statistics in JSON format (Auto-detected for .json).')

    # Group: Content Formatting
    enc_group = parser.add_argument_group('Content Formatting')
    enc_group.add_argument('--nolabel', action='store_true',
                        help="Input file does not have field labels (like '|cost|' or '|text|').")
    enc_group.add_argument('--nolinetrans', action='store_true',
                        help='Input file does not use automatic line reordering.')

    # Group: Data Processing
    proc_group = parser.add_argument_group('Data Processing')
    proc_group.add_argument('-x', '--outliers', action='store_true',
                        help='Show extra details and unusual cards.')
    proc_group.add_argument('-a', '--all', action='store_true',
                        help='Show all information and dump invalid cards.')
    proc_group.add_argument('-n', '--limit', type=int, default=0,
                        help='Only process the first N cards.')
    proc_group.add_argument('--shuffle', action='store_true',
                        help='Randomize the order of cards before summarizing.')
    proc_group.add_argument('-t', '--top', type=int, default=10,
                        help='Limit the number of entries in breakdown tables.')
    proc_group.add_argument('--seed', type=int,
                        help='Seed for the random number generator.')
    proc_group.add_argument('--sample', type=int, default=0,
                        help='Pick N random cards from the input (shorthand for --shuffle --limit N).')
    proc_group.add_argument('--sort', choices=['name', 'color', 'identity', 'type', 'cmc', 'rarity', 'power', 'toughness', 'loyalty', 'set', 'pack'],
                        help='Sort cards by a specific criterion.')

    # Group: Filtering Options
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('--booster', type=int, default=0,
                        help='Simulate opening N booster packs. Distribution: 10 Common, 3 Uncommon, 1 Rare/Mythic, 1 Basic Land. Shuffles by default.')
    filter_group.add_argument('--box', type=int, default=0,
                        help='Simulate opening N booster boxes (36 packs each). Shuffles by default.')
    filter_group.add_argument('--grep', action='append',
                        help='Only include cards matching a search pattern (checks name, typeline, text, cost, and stats). Use multiple times for AND logic.')
    filter_group.add_argument('--grep-name', action='append',
                        help='Only include cards whose name matches a search pattern.')
    filter_group.add_argument('--grep-type', action='append',
                        help='Only include cards whose typeline matches a search pattern.')
    filter_group.add_argument('--grep-text', action='append',
                        help='Only include cards whose rules text matches a search pattern.')
    filter_group.add_argument('--grep-cost', action='append',
                        help='Only include cards whose mana cost matches a search pattern.')
    filter_group.add_argument('--grep-pt', action='append',
                        help='Only include cards whose power/toughness matches a search pattern.')
    filter_group.add_argument('--grep-loyalty', action='append',
                        help='Only include cards whose loyalty/defense matches a search pattern.')
    filter_group.add_argument('--vgrep', '--exclude', action='append',
                        help='Skip cards matching a search pattern (checks name, typeline, text, cost, and stats). Use multiple times for OR logic.')
    filter_group.add_argument('--exclude-name', action='append',
                        help='Exclude cards whose name matches a search pattern.')
    filter_group.add_argument('--exclude-type', action='append',
                        help='Exclude cards whose typeline matches a search pattern.')
    filter_group.add_argument('--exclude-text', action='append',
                        help='Exclude cards whose rules text matches a search pattern.')
    filter_group.add_argument('--exclude-cost', action='append',
                        help='Exclude cards whose mana cost matches a search pattern.')
    filter_group.add_argument('--exclude-pt', action='append',
                        help='Exclude cards whose power/toughness matches a search pattern.')
    filter_group.add_argument('--exclude-loyalty', action='append',
                        help='Exclude cards whose loyalty/defense matches a search pattern.')
    filter_group.add_argument('--set', action='append',
                        help='Only include cards from specific sets (e.g., MOM, MRD). Supports multiple sets (OR logic).')
    filter_group.add_argument('--rarity', action='append',
                        help="Only include cards of specific rarities. Supports full names (e.g., 'common', 'mythic') or shorthands: O (Common), N (Uncommon), A (Rare), Y (Mythic), I (Special), L (Basic Land). Supports multiple values (OR logic).")
    filter_group.add_argument('--colors', action='append',
                        help="Only include cards of specific colors (W, U, B, R, G). Use 'C' or 'A' for colorless. Supports multiple values (OR logic).")
    filter_group.add_argument('--identity', action='append',
                        help="Only include cards with specific colors in their color identity (W, U, B, R, G). Use 'C' or 'A' for colorless. Supports multiple values (OR logic).")
    filter_group.add_argument('--id-count', action='append',
                        help='Only include cards with specific color identity counts. Supports inequalities, ranges, and multiple values (OR logic).')
    filter_group.add_argument('--cmc', action='append',
                        help='Only include cards with specific CMC (Converted Mana Cost) values. Supports inequalities (e.g., ">3", "<=2"), ranges (e.g., "1-4"), and multiple values (OR logic).')
    filter_group.add_argument('--pow', '--power', action='append', dest='pow',
                        help='Only include cards with specific Power values. Supports inequalities, ranges, and multiple values (OR logic).')
    filter_group.add_argument('--tou', '--toughness', action='append', dest='tou',
                        help='Only include cards with specific Toughness values. Supports inequalities, ranges, and multiple values (OR logic).')
    filter_group.add_argument('--loy', '--loyalty', '--defense', action='append', dest='loy',
                        help='Only include cards with specific Loyalty or Defense values. Supports inequalities, ranges, and multiple values (OR logic).')
    filter_group.add_argument('--mechanic', action='append',
                        help='Only include cards with specific mechanical features or keyword abilities (e.g., Flying, Activated, ETB Effect). Supports multiple values (OR logic).')
    filter_group.add_argument('--deck-filter', '--decklist-filter', dest='deck',
                        help='Filter cards using a standard MTG decklist file. Also multiplies cards in the output based on their counts in the decklist.')
    
    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true',
                        help='Enable detailed status messages.')
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

    main(args.infile, verbose = args.verbose, outliers = args.outliers, dump_all = args.all,
         nolinetrans = args.nolinetrans, nolabel = args.nolabel,
         grep = args.grep, use_color = args.color, limit = args.limit, json_out = args.json, vgrep = args.vgrep,
         grep_name=args.grep_name, vgrep_name=args.exclude_name,
         grep_types=args.grep_type, vgrep_types=args.exclude_type,
         grep_text=args.grep_text, vgrep_text=args.exclude_text,
         grep_cost=args.grep_cost, vgrep_cost=args.exclude_cost,
         grep_pt=args.grep_pt, vgrep_pt=args.exclude_pt,
         grep_loyalty=args.grep_loyalty, vgrep_loyalty=args.exclude_loyalty,
         sets = args.set, rarities = args.rarity, colors=args.colors, cmcs=args.cmc,
         pows=args.pow, tous=args.tou, loys=args.loy,
         mechanics=args.mechanic,
         identities=args.identity, id_counts=args.id_count,
         shuffle = args.shuffle, seed = args.seed, quiet = args.quiet, oname = args.outfile, decklist_file = args.deck,
         top = args.top, booster = args.booster, sort = args.sort, box = args.box)
    exit(0)
