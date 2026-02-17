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

# Try to import tqdm for progress bars
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

def sortcards(cards, verbose=False):
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
    ])

    iterator = cards
    if verbose:
        iterator = tqdm(cards, desc="Sorting cards", unit="card")

    for card in iterator:
        # Use card.raw for the original string representation
        # Ensure we have a string to write out
        card_str = card.raw if card.raw else card.encode()

        # special classes
        # Check if it's a split card (has a bside)
        if card.bside:
            # Reconstruct the split separator if needed, though card.raw usually has it.
            # But the original code did a replace to visualize the split.
            # Let's check if the raw string has the separator.
            if utils.bsidesep in card_str:
                 card_str = card_str.replace(utils.bsidesep, '|\n~~~~~~~~~~~~~~~~\n|')
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
        elif 'land' in types:
            classes['lands'].append(card_str)
        elif 'instant' in types:
            classes['instants'].append(card_str)
        elif 'sorcery' in types:
            classes['sorceries'].append(card_str)
        elif 'enchantment' in types:
            classes['enchantments'].append(card_str)
        elif 'artifact' in types:
            # Check for artifact creature
            if 'creature' in types:
                classes['creatures'].append(card_str)
            else:
                classes['noncreature artifacts'].append(card_str)
        elif 'creature' in types:
            classes['creatures'].append(card_str)
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
        
    return classes


def main():
    parser = argparse.ArgumentParser(
        description="""Sorts encoded Magic cards into categories (e.g., by color, type) and formats them for forum posts.

Supports any encoding format supported by encode.py/decode.py.""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Path to the encoded card file to sort. Defaults to stdin (-).')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save the output. If not provided, output prints to the console (stdout).')

    # Group: Encoding Options
    enc_group = parser.add_argument_group('Encoding Options')
    enc_group.add_argument('-e', '--encoding', default='std', choices=utils.formats,
                        help="Card data format: 'std' (name last, default), 'named' (name first), "
                             "'noname' (no name), 'rfields' (random field order), "
                             "'old' (legacy), 'norarity' (no rarity), 'vec' (vectorized), "
                             "or 'custom' (user-defined).")

    # Group: Processing Options
    proc_group = parser.add_argument_group('Processing Options')
    proc_group.add_argument('-n', '--limit', type=int, default=0,
                        help='Limit the number of cards to sort.')
    proc_group.add_argument('--grep', action='append',
                        help='Filter cards by regex (matches name, type, or text). Can be used multiple times (AND logic).')
    proc_group.add_argument('--vgrep', '--exclude', action='append',
                        help='Exclude cards matching regex (matches name, type, or text). Can be used multiple times (OR logic).')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output, including loading diagnostics.')
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

    # Use the robust jdecode.mtg_open_file for loading and filtering.
    # We disable default exclusions (sets, types, layouts) to match the original sortcards.py behavior.
    # verbose=True enables jdecode diagnostic output (e.g. invalid cards).
    cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose, fmt_ordered=fmt_ordered, grep=args.grep, vgrep=args.vgrep,
                                  exclude_sets=lambda x: False,
                                  exclude_types=lambda x: False,
                                  exclude_layouts=lambda x: False)

    if args.limit > 0:
        cards = cards[:args.limit]

    # Progress bar is shown unless --quiet is specified
    classes = sortcards(cards, verbose=not args.quiet)

    outputter = sys.stdout
    ofile = None

    if args.outfile:
        if args.verbose:
            print(f'Writing output to: {args.outfile}', file=sys.stderr)
        try:
            ofile = open(args.outfile, 'w', encoding='utf-8')
            outputter = ofile
        except Exception as e:
            print(f"Error opening output file {args.outfile}: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        # Determine if we should use color for the summary
        use_color = False
        if args.color is True:
            use_color = True
        elif args.color is None and sys.stderr.isatty():
            use_color = True

        # Print summary (to stderr to separate from data)
        # Summary is shown unless --quiet is specified
        for cardclass, card_list in classes.items():
            if card_list is None:
                if not args.quiet:
                    header = cardclass
                    if use_color:
                        header = utils.colorize(header, utils.Ansi.BOLD + utils.Ansi.CYAN)
                    print(header, file=sys.stderr)
            else:
                if not args.quiet:
                    name = cardclass
                    count = str(len(card_list))
                    if use_color:
                        if len(card_list) > 0:
                            count = utils.colorize(count, utils.Ansi.BOLD + utils.Ansi.GREEN)
                    print(f'  {name}: {count}', file=sys.stderr)

        # Write content
        for cardclass, card_list in classes.items():
            if card_list is None:
                outputter.write(f'{cardclass}\n')
            else:
                classlen = len(card_list)
                if classlen > 0:
                    outputter.write(f'[spoiler={cardclass}: {classlen} cards]\n')
                    for card_str in card_list:
                        outputter.write(f'{card_str}\n\n')
                    outputter.write('[/spoiler]\n')

    finally:
        if ofile:
            ofile.close()

if __name__ == '__main__':
    main()
