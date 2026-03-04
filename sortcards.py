#!/usr/bin/env python3
import sys
import os
import argparse
from collections import OrderedDict

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
sys.path.append(libdir)

import cardlib
import utils
import jdecode
import sortlib

# Try to import tqdm for progress bars
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

def sortcards(cards, verbose=False, use_summary=False, use_color=False, fmt_ordered=cardlib.fmt_ordered_default):
    """
    Sorts a list of Card objects into various categories.
    """
    classes = OrderedDict([
        ('Special classes:', None),
        ('multicards', []),
        ('Inclusive classes:', None),
        ('X cards', []),
        ('kicker cards', []),
        ('counter cards', []),
        ('uncast cards', []),
        ('choice cards', []),
        ('equipment', []),
        ('levelers', []),
        ('legendary', []),
        ('Exclusive classes:', None),
        ('battles', []),
        ('planeswalkers', []),
        ('lands', []),
        ('instants', []),
        ('sorceries', []),
        ('enchantments', []),
        ('noncreature artifacts', []),
        ('creatures', []),
        ('other', []),
        ('By color:', None),
        ('white', []),
        ('blue', []),
        ('black', []),
        ('red', []),
        ('green', []),
        ('colorless nonland', []),
        ('colorless land', []),
        ('unknown color', []),
        ('By number of colors:', None),
        ('zero colors', []),                
        ('one color', []),
        ('two colors', []),
        ('three colors', []),
        ('four colors', []),
        ('five colors', []),
        ('6+ colors', []),
        ('By rarity:', None),
        ('common', []),
        ('uncommon', []),
        ('rare', []),
        ('mythic', []),
        ('special', []),
        ('basic land', []),
        ('unknown rarity', []),
        ('By CMC:', None),
        ('CMC 0', []),
        ('CMC 1', []),
        ('CMC 2', []),
        ('CMC 3', []),
        ('CMC 4', []),
        ('CMC 5', []),
        ('CMC 6', []),
        ('CMC 7+', []),
    ])

    iterator = cards
    if verbose:
        iterator = tqdm(cards, desc="Sorting cards", unit="card")

    for card in iterator:
        # Determine the string representation to use
        if use_summary:
            card_str = card.summary(ansi_color=use_color)
        else:
            # Use card.raw for the original string representation
            # Ensure we have a string to write out
            card_str = card.raw if card.raw else card.encode(fmt_ordered=fmt_ordered)

        # special classes
        # Check if it's a split card (has a bside)
        if card.bside:
            # Reconstruct the split separator if needed, though card.raw usually has it.
            # But the original code did a replace to visualize the split.
            # Let's check if the raw string has the separator.
            if utils.bsidesep in card_str:
                 card_str = card_str.replace(utils.bsidesep, ' // ')
            classes['multicards'].append(card_str)
            continue
        
        # Inclusive classes - checking text/types/etc
        # We check the raw string for some of these to match original behavior (like 'X' or symbols)
        # But we can also use structured data.

        if 'X' in card_str:
            classes['X cards'].append(card_str)

        if 'kick' in card.text.text:
             classes['kicker cards'].append(card_str)

        # Counters usually have % or # in the encoded text
        if '%' in card_str or '#' in card_str:
            classes['counter cards'].append(card_str)

        if 'uncast' in card.text.text:
            classes['uncast cards'].append(card_str)

        # Choice cards have delimiters like [ or =
        if '[' in card_str or ']' in card_str or '=' in card_str:
             classes['choice cards'].append(card_str)

        if 'equipment' in card.subtypes or 'equip' in card.text.text:
            classes['equipment'].append(card_str)

        if 'level up' in card.text.text or 'level &' in card_str:
            classes['levelers'].append(card_str)

        if 'legendary' in card.supertypes:
             classes['legendary'].append(card_str)

        # exclusive classes
        # Check types list
        types = [t.lower() for t in card.types]

        if 'battle' in types:
            classes['battles'].append(card_str)
        elif 'planeswalker' in types:
            classes['planeswalkers'].append(card_str)
        elif 'creature' in types:
            classes['creatures'].append(card_str)
        elif 'land' in types:
            classes['lands'].append(card_str)
        elif 'instant' in types:
            classes['instants'].append(card_str)
        elif 'sorcery' in types:
            classes['sorceries'].append(card_str)
        elif 'enchantment' in types:
            classes['enchantments'].append(card_str)
        elif 'artifact' in types:
            classes['noncreature artifacts'].append(card_str)
        else:
            classes['other'].append(card_str)

        # color classes
        colors = card.cost.colors

        color_count = 0
        if colors:
            if 'W' in colors:
                classes['white'].append(card_str)
                color_count += 1
            if 'U' in colors:
                classes['blue'].append(card_str)
                color_count += 1
            if 'B' in colors:
                classes['black'].append(card_str)
                color_count += 1
            if 'R' in colors:
                classes['red'].append(card_str)
                color_count += 1
            if 'G' in colors:
                classes['green'].append(card_str)
                color_count += 1
        else:
            # No colors (colorless)
            if 'land' in types:
                classes['colorless land'].append(card_str)
            else:
                classes['colorless nonland'].append(card_str)

        # Count based categories
        if color_count == 0:
            classes['zero colors'].append(card_str)
        elif color_count == 1:
            classes['one color'].append(card_str)
        elif color_count == 2:
            classes['two colors'].append(card_str)
        elif color_count == 3:
            classes['three colors'].append(card_str)
        elif color_count == 4:
            classes['four colors'].append(card_str)
        elif color_count == 5:
            classes['five colors'].append(card_str)
        else:
            classes['6+ colors'].append(card_str)

        # rarity classes
        rarity = card.rarity
        if rarity in [utils.rarity_common_marker, 'common']:
            classes['common'].append(card_str)
        elif rarity in [utils.rarity_uncommon_marker, 'uncommon']:
            classes['uncommon'].append(card_str)
        elif rarity in [utils.rarity_rare_marker, 'rare']:
            classes['rare'].append(card_str)
        elif rarity in [utils.rarity_mythic_marker, 'mythic', 'mythic rare']:
            classes['mythic'].append(card_str)
        elif rarity in [utils.rarity_special_marker, 'special']:
            classes['special'].append(card_str)
        elif rarity in [utils.rarity_basic_land_marker, 'basic land']:
            classes['basic land'].append(card_str)
        else:
            classes['unknown rarity'].append(card_str)

        # CMC classes
        cmc = card.cost.cmc
        if cmc == 0:
            classes['CMC 0'].append(card_str)
        elif cmc == 1:
            classes['CMC 1'].append(card_str)
        elif cmc == 2:
            classes['CMC 2'].append(card_str)
        elif cmc == 3:
            classes['CMC 3'].append(card_str)
        elif cmc == 4:
            classes['CMC 4'].append(card_str)
        elif cmc == 5:
            classes['CMC 5'].append(card_str)
        elif cmc == 6:
            classes['CMC 6'].append(card_str)
        elif cmc >= 7:
            classes['CMC 7+'].append(card_str)
        
    return classes


def main(fname, oname = None, verbose = True, encoding = 'std',
         nolinetrans = False, nolabel = False,
         use_summary = False, use_color = None, quiet = False,
         limit = 0, grep = None, sort = None, vgrep = None,
         grep_name=None, vgrep_name=None, grep_types=None, vgrep_types=None,
         grep_text=None, vgrep_text=None,
         grep_cost=None, vgrep_cost=None, grep_pt=None, vgrep_pt=None,
         grep_loyalty=None, vgrep_loyalty=None,
         sets = None, rarities = None, colors=None, cmcs=None,
         shuffle = False, seed = None, decklist_file = None):

    # Determine format
    fmt_ordered = cardlib.fmt_ordered_default
    if encoding == 'named':
        fmt_ordered = cardlib.fmt_ordered_named
    elif encoding == 'noname':
        fmt_ordered = cardlib.fmt_ordered_noname
    elif encoding == 'old':
        fmt_ordered = cardlib.fmt_ordered_old
    elif encoding == 'norarity':
        fmt_ordered = cardlib.fmt_ordered_norarity

    # Use the robust jdecode.mtg_open_file for loading and filtering.
    # We disable default exclusions (sets, types, layouts) to match the original sortcards.py behavior.
    # verbose=True enables jdecode diagnostic output (e.g. invalid cards).
    cards = jdecode.mtg_open_file(fname, verbose=verbose, linetrans=not nolinetrans,
                                  fmt_ordered=fmt_ordered, fmt_labeled=None if nolabel else cardlib.fmt_labeled_default,
                                  grep=grep, vgrep=vgrep,
                                  grep_name=grep_name, vgrep_name=vgrep_name,
                                  grep_types=grep_types, vgrep_types=vgrep_types,
                                  grep_text=grep_text, vgrep_text=vgrep_text,
                                  grep_cost=grep_cost, vgrep_cost=vgrep_cost,
                                  grep_pt=grep_pt, vgrep_pt=vgrep_pt,
                                  grep_loyalty=grep_loyalty, vgrep_loyalty=vgrep_loyalty,
                                  sets=sets, rarities=rarities,
                                  colors=colors, cmcs=cmcs,
                                  exclude_sets=lambda x: False,
                                  exclude_types=lambda x: False,
                                  exclude_layouts=lambda x: False,
                                  shuffle=shuffle, seed=seed,
                                  decklist_file=decklist_file)

    if sort:
        cards = sortlib.sort_cards(cards, sort, quiet=quiet)

    if limit > 0:
        cards = cards[:limit]

    # Determine if we should use color for the summary
    actual_use_color = False
    if use_color is True:
        actual_use_color = True
    elif use_color is None and sys.stderr.isatty():
        actual_use_color = True

    # Progress bar is shown unless --quiet is specified
    classes = sortcards(cards, verbose=not quiet, use_summary=use_summary, use_color=actual_use_color, fmt_ordered=fmt_ordered)

    outputter = sys.stdout
    ofile = None

    if oname:
        if verbose:
            print(f'Writing output to: {oname}', file=sys.stderr)
        try:
            ofile = open(oname, 'w', encoding='utf-8')
            outputter = ofile
        except Exception as e:
            print(f"Error opening output file {oname}: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        # Re-organize reporting to suppress empty sections/categories
        # This implementation uses a "look-ahead" to only print headers if they contain cards.

        # Step 1: Group categories by their headers
        sections = OrderedDict()
        current_header = "General:"
        sections[current_header] = []
        for key, value in classes.items():
            if value is None:
                current_header = key
                sections[current_header] = []
            else:
                sections[current_header].append((key, value))

        # Print summary (to stderr) and write content (to outputter)
        for header, categories in sections.items():
            # Check if any category in this section has cards
            non_empty_categories = [(cat, cards) for cat, cards in categories if cards]

            if non_empty_categories:
                # Print Header
                if not quiet:
                    display_header = header
                    if actual_use_color:
                        display_header = utils.colorize(display_header, utils.Ansi.BOLD + utils.Ansi.CYAN)
                    print(display_header, file=sys.stderr)
                outputter.write(f'{header}\n')

                for name, card_list in non_empty_categories:
                    # Summary line
                    if not quiet:
                        count_str = str(len(card_list))
                        if actual_use_color:
                            count_str = utils.colorize(count_str, utils.Ansi.BOLD + utils.Ansi.GREEN)
                        print(f'  {name}: {count_str}', file=sys.stderr)

                    # Content block
                    classlen = len(card_list)
                    outputter.write(f'[spoiler={name}: {classlen} cards]\n')
                    for card_str in card_list:
                        outputter.write(f'{card_str}\n\n')
                    outputter.write('[/spoiler]\n')

    finally:
        if ofile:
            ofile.close()

def cli():
    parser = argparse.ArgumentParser(
        description="""Sort Magic cards into groups (like color or type) and format them for sharing on forums.

Supports any encoding format supported by encode.py/decode.py.""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

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
                             "or 'custom' (User-defined).")
    enc_group.add_argument('--nolabel', action='store_true',
                        help="Input file does not have field labels (like '|cost|' or '|text|').")
    enc_group.add_argument('--nolinetrans', action='store_true',
                        help='Input file does not use automatic line reordering.')

    # Group: Processing Options
    proc_group = parser.add_argument_group('Processing Options')
    proc_group.add_argument('-n', '--limit', type=int, default=0,
                        help='Only process the first N cards.')
    proc_group.add_argument('--sort', choices=['name', 'color', 'type', 'cmc'],
                        help='Sort cards by a specific criterion.')
    proc_group.add_argument('--shuffle', action='store_true',
                        help='Randomize the order of cards before sorting.')
    proc_group.add_argument('--seed', type=int,
                        help='Seed for the random number generator.')
    proc_group.add_argument('--sample', type=int, default=0,
                        help='Pick N random cards from the input (shorthand for --shuffle --limit N).')
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
    proc_group.add_argument('--summary', action='store_true',
                        help='Output compact card summaries instead of full encoded text.')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true',
                        help='Enable detailed status messages.')
    debug_group.add_argument('-q', '--quiet', action='store_true',
                        help='Suppress all non-error output (progress bars and summary).')

    # Color options
    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None,
                        help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color',
                        help='Disable ANSI color output.')

    args = parser.parse_args()

    # Determine format
    fmt_ordered = cardlib.fmt_ordered_default
    if args.encoding == 'named':
        fmt_ordered = cardlib.fmt_ordered_named
    elif args.encoding == 'noname':
        fmt_ordered = cardlib.fmt_ordered_noname
    elif args.encoding == 'old':
        fmt_ordered = cardlib.fmt_ordered_old
    elif args.encoding == 'norarity':
        fmt_ordered = cardlib.fmt_ordered_norarity

    # We could support custom formats if needed, but this covers the main ones.

    # Handle --sample
    if args.sample > 0:
        args.shuffle = True
        args.limit = args.sample

    main(args.infile, args.outfile, verbose = args.verbose, encoding = args.encoding,
         nolinetrans = args.nolinetrans, nolabel = args.nolabel,
         use_summary = args.summary, use_color = args.color, quiet = args.quiet,
         limit = args.limit, grep = args.grep, sort = args.sort, vgrep = args.vgrep,
         grep_name=args.grep_name, vgrep_name=args.exclude_name,
         grep_types=args.grep_type, vgrep_types=args.exclude_type,
         grep_text=args.grep_text, vgrep_text=args.exclude_text,
         grep_cost=args.grep_cost, vgrep_cost=args.exclude_cost,
         grep_pt=args.grep_pt, vgrep_pt=args.exclude_pt,
         grep_loyalty=args.grep_loyalty, vgrep_loyalty=args.exclude_loyalty,
         sets = args.set, rarities = args.rarity, colors=args.colors, cmcs=args.cmc,
         shuffle = args.shuffle, seed = args.seed, decklist_file = args.deck)

if __name__ == '__main__':
    cli()
