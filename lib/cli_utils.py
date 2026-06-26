# Copyright 2026 Google LLC
import sys
import os
import argparse
import jdecode

def add_standard_filters(parser):
    """Adds standard MTG filtering arguments to an argparse parser or group."""
    if isinstance(parser, argparse.ArgumentParser):
        filter_group = parser.add_argument_group('Filtering Options')
    else:
        filter_group = parser

    filter_group.add_argument('-g', '--grep', action='append',
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
                        help='Only include cards from specific sets (e.g., MOM, MRD). Supports multiple values (OR logic).')
    filter_group.add_argument('--rarity', action='append',
                        help="Only include cards of specific rarities. Supports full names (e.g., 'common', 'mythic') or shorthands: "
                             "O (Common), N (Uncommon), A (Rare), Y (Mythic), I (Special), or L (Basic Land). "
                             "Supports multiple values (OR logic).")
    filter_group.add_argument('--colors', action='append',
                        help="Only include cards of specific colors (W, U, B, R, G). Use 'C' or 'A' for colorless. "
                             "Supports multiple values (OR logic).")
    filter_group.add_argument('--identity', action='append',
                        help="Only include cards with specific colors in their color identity (W, U, B, R, G). "
                             "Use 'C' or 'A' for colorless. Supports multiple values (OR logic).")
    filter_group.add_argument('--produces', action='append',
                        help="Only include cards that can produce specific colors of mana (W, U, B, R, G, C, or Any). "
                             "Matching a specific color also includes cards that produce 'Any'. Supports multiple values (OR logic).")
    filter_group.add_argument('--id-count', action='append',
                        help='Only include cards with specific color identity counts. Supports exact values ("2"), '
                             'inequalities (e.g., ">3", "<=2"), ranges (e.g., "1-4"), and multiple values (OR logic).')
    filter_group.add_argument('--cmc', action='append',
                        help='Only include cards with specific CMC (Converted Mana Cost) values. Supports exact values, '
                             'inequalities (e.g., ">3", "<=2"), ranges (e.g., "1-4"), and multiple values (OR logic).')
    filter_group.add_argument('--pow', '--power', action='append', dest='pow',
                        help='Only include cards with specific Power values. Supports exact values, '
                             'inequalities, ranges, and multiple values (OR logic).')
    filter_group.add_argument('--tou', '--toughness', action='append', dest='tou',
                        help='Only include cards with specific Toughness values. Supports exact values, '
                             'inequalities, ranges, and multiple values (OR logic).')
    filter_group.add_argument('--loy', '--loyalty', '--defense', action='append', dest='loy',
                        help='Only include cards with specific Loyalty or Defense values. Supports exact values, '
                             'inequalities, ranges, and multiple values (OR logic).')
    filter_group.add_argument('--complexity', '--score', action='append',
                        help='Only include cards with specific design complexity scores. Supports inequalities and ranges.')
    filter_group.add_argument('--rating', '--power-rating', action='append', dest='rating',
                        help='Only include cards with specific power ratings (efficiency vs CMC). Supports inequalities and ranges.')
    filter_group.add_argument('--fair-mv', '--fcmc', '--recommended-cmc', action='append', dest='fair_mv',
                        help='Only include cards with specific recommended Fair Mana Values. Supports inequalities and ranges.')
    filter_group.add_argument('--mechanic', action='append',
                        help='Only include cards with specific mechanical features or keyword abilities (e.g., Flying, Activated, ETB Effect). '
                             'Supports multiple values (OR logic).')
    filter_group.add_argument('--action', action='append',
                        help='Only include cards with specific functional actions (Removal, Protection, Buffs, Card Advantage, Disruption, or Mana). '
                             'Supports multiple values (OR logic).')
    filter_group.add_argument('--color-pie-break', action='store_true',
                        help='Only include cards that violate the mechanical color pie (e.g. Green cards with Haste).')
    filter_group.add_argument('--deck-filter', '--decklist-filter', dest='deck',
                        help='Filter cards using a standard MTG decklist file. Also multiplies cards in the output based on their counts in the decklist.')
    filter_group.add_argument('--booster', type=int, default=0,
                        help='Simulate opening N booster packs. Distribution: 10 Common, 3 Uncommon, 1 Rare/Mythic, 1 Basic Land.')
    filter_group.add_argument('--box', type=int, default=0,
                        help='Simulate opening N booster boxes (36 packs each).')
    filter_group.add_argument('-n', '--limit', type=int, default=0,
                        help='Only process the first N cards.')
    filter_group.add_argument('--shuffle', action='store_true',
                        help='Shuffle the cards before processing.')
    filter_group.add_argument('--sample', type=int, default=0,
                        help='Pick N random cards (shorthand for --shuffle --limit N).')
    filter_group.add_argument('--seed', type=int,
                        help='Seed for the random number generator.')

def add_standard_output_args(parser):
    """Adds standard output flags to an argparse parser or group."""
    if isinstance(parser, argparse.ArgumentParser):
        output_group = parser.add_argument_group('Output Format')
    else:
        output_group = parser

    fmt_group = output_group.add_mutually_exclusive_group()
    fmt_group.add_argument('-j', '--json', action='store_true', help='Generate JSON output.')
    fmt_group.add_argument('--csv', action='store_true', help='Generate CSV output.')
    fmt_group.add_argument('-t', '--table', action='store_true', help='Generate a formatted table.')
    
    if isinstance(parser, argparse.ArgumentParser):
        debug_group = parser.add_argument_group('Logging & Debugging')
    else:
        # If we passed a group, we might want to add to the parser instead, but usually we just want to add these arguments
        debug_group = parser
        
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    debug_group.add_argument('-q', '--quiet', action='store_true', help='Suppress status messages.')

    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color output.')

def load_and_filter_cards(args):
    """Loads and filters cards based on standard arguments."""
    # Resolve smart defaults for infile
    infile = getattr(args, 'infile', '-')
    outfile = getattr(args, 'outfile', None)
    
    # Logic from mtg_search.py for smart infile handling
    if infile and infile != '-' and not os.path.exists(infile):
        # If there are 2 positional arguments and the first isn't a file but the second is, swap them.
        if outfile and os.path.exists(outfile):
            query = infile
            infile = outfile
            setattr(args, 'outfile', None)
            if not getattr(args, 'grep', None):
                setattr(args, 'grep', [query])
            else:
                getattr(args, 'grep').append(query)
        # If only one argument was provided (or both don't exist), treat it as a query.
        else:
            if not getattr(args, 'grep', None):
                setattr(args, 'grep', [infile])
            else:
                getattr(args, 'grep').append(infile)
            infile = '-'

    if infile == '-' and sys.stdin.isatty():
        script_dir = os.path.dirname(os.path.realpath(__file__))
        # Try a few common locations for AllPrintings.json
        options = [
            os.path.join(script_dir, '../data/AllPrintings.json'),
            'data/AllPrintings.json',
            os.path.join(os.path.dirname(script_dir), 'data/AllPrintings.json'),
            os.path.join(os.path.dirname(os.path.dirname(script_dir)), 'data/AllPrintings.json')
        ]
        for opt in options:
            if os.path.exists(opt):
                infile = opt
                if not getattr(args, 'quiet', False):
                    print(f"Notice: Using default dataset: {infile}", file=sys.stderr)
                break
    
    setattr(args, 'infile', infile)

    # Handle --sample
    limit = getattr(args, 'limit', 0)
    shuffle = getattr(args, 'shuffle', False)
    if getattr(args, 'sample', 0) > 0:
        shuffle = True
        limit = args.sample

    cards = jdecode.mtg_open_file(infile, verbose=getattr(args, 'verbose', False),
                                  grep=getattr(args, 'grep', None), 
                                  vgrep=getattr(args, 'vgrep', None),
                                  grep_name=getattr(args, 'grep_name', None), 
                                  vgrep_name=getattr(args, 'exclude_name', None),
                                  grep_types=getattr(args, 'grep_type', None), 
                                  vgrep_types=getattr(args, 'exclude_type', None),
                                  grep_text=getattr(args, 'grep_text', None), 
                                  vgrep_text=getattr(args, 'exclude_text', None),
                                  grep_cost=getattr(args, 'grep_cost', None), 
                                  vgrep_cost=getattr(args, 'exclude_cost', None),
                                  grep_pt=getattr(args, 'grep_pt', None), 
                                  vgrep_pt=getattr(args, 'exclude_pt', None),
                                  grep_loyalty=getattr(args, 'grep_loyalty', None), 
                                  vgrep_loyalty=getattr(args, 'exclude_loyalty', None),
                                  sets=getattr(args, 'set', None), 
                                  rarities=getattr(args, 'rarity', None),
                                  colors=getattr(args, 'colors', None), 
                                  cmcs=getattr(args, 'cmc', None),
                                  pows=getattr(args, 'pow', None), 
                                  tous=getattr(args, 'tou', None), 
                                  loys=getattr(args, 'loy', None),
                                  mechanics=getattr(args, 'mechanic', None),
                                  actions=getattr(args, 'action', None),
                                  produces=getattr(args, 'produces', None),
                                  color_pie_break=getattr(args, 'color_pie_break', False),
                                  identities=getattr(args, 'identity', None), 
                                  id_counts=getattr(args, 'id_count', None),
                                  complexities=getattr(args, 'complexity', None),
                                  ratings=getattr(args, 'rating', None),
                                  fair_mvs=getattr(args, 'fair_mv', None),
                                  decklist_file=getattr(args, 'deck', None),
                                  booster=getattr(args, 'booster', 0), 
                                  box=getattr(args, 'box', 0),
                                  shuffle=shuffle, 
                                  seed=getattr(args, 'seed', None))
    
    if limit > 0:
        cards = cards[:limit]
        
    return cards
