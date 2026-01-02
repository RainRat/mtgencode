#!/usr/bin/env python3
import sys
import os
import argparse
from collections import OrderedDict

# Set up lib path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'lib')
sys.path.append(libdir)

import cardlib
import utils

# Try to import tqdm for progress bars
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

def sortcards(cards, verbose=False, fmt_ordered=None):
    """
    Sorts a list of encoded card strings into various categories.
    """
    if fmt_ordered is None:
        fmt_ordered = cardlib.fmt_ordered_default

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
        ('more colors?', []),
    ])

    iterator = cards
    if verbose:
        iterator = tqdm(cards, desc="Sorting cards", unit="card")

    for card_src in iterator:
        # Parse the card string into a Card object
        try:
            # We use fmt_labeled_default because the encoder typically produces labeled output
            card = cardlib.Card(card_src, fmt_ordered=fmt_ordered)
        except Exception:
            # If parsing fails, dump to 'other' and continue
            classes['other'] += [card_src]
            continue

        # If card is invalid/unparsed but we want to keep the string, put in 'other'
        # But Card() usually creates an object even if fields are missing/weird.
        # We'll use the original string 'card_src' for output to preserve exact text.

        # special classes - using raw string checks for these
        if '|\n|' in card_src:
            classes['multicards'] += [card_src.replace('|\n|', '|\n~~~~~~~~~~~~~~~~\n|')]
            continue
        
        # inclusive classes - checks on raw string or parsed fields
        # Using raw string is safer for preserving existing behavior for simple substrings
        if 'X' in card_src:
            classes['X cards'] += [card_src]
        if 'kick' in card_src:
            classes['kicker cards'] += [card_src]
        if '%' in card_src or '#' in card_src:
            classes['counter cards'] += [card_src]
        if 'uncast' in card_src:
            classes['uncast cards'] += [card_src]
        if '[' in card_src or ']' in card_src or '=' in card_src:
            classes['choice cards'] += [card_src]

        # Checking types using parsed card object
        types = [t.lower() for t in card.types]
        subtypes = [s.lower() for s in card.subtypes]

        if 'equipment' in subtypes or 'equip {' in card_src:
            classes['equipment'] += [card_src]
        if 'level up' in card_src or 'level &' in card_src:
            classes['levelers'] += [card_src]
        if 'legendary' in card.supertypes: # supertypes are already lowercased in Card
            classes['legendary'] += [card_src]

        # exclusive classes
        # Use card.types which is robust
        if 'battle' in types:
            classes['battles'] += [card_src]
        elif 'planeswalker' in types:
            classes['planeswalkers'] += [card_src]
        elif 'land' in types:
            classes['lands'] += [card_src]
        elif 'instant' in types:
            classes['instants'] += [card_src]
        elif 'sorcery' in types:
            classes['sorceries'] += [card_src]
        elif 'enchantment' in types:
            classes['enchantments'] += [card_src]
        elif 'artifact' in types:
            classes['noncreature artifacts'] += [card_src]
        elif 'creature' in types or 'artifact creature' in card_src: # Fallback for old check
            classes['creatures'] += [card_src]
        else:
            classes['other'] += [card_src]

        # color classes
        colors = card.cost.colors

        # Manacost.colors is a string like "WUBRG"
        # Determine specific colors
        is_white = 'W' in colors
        is_blue = 'U' in colors
        is_black = 'B' in colors
        is_red = 'R' in colors
        is_green = 'G' in colors

        # Populate "By color"
        if is_white: classes['white'] += [card_src]
        if is_blue: classes['blue'] += [card_src]
        if is_black: classes['black'] += [card_src]
        if is_red: classes['red'] += [card_src]
        if is_green: classes['green'] += [card_src]

        color_count = len(colors)

        # Colorless logic
        if color_count == 0:
            if 'land' in types:
                classes['colorless land'] += [card_src]
            else:
                classes['colorless nonland'] += [card_src]

        # By number of colors
        if color_count == 0:
            classes['zero colors'] += [card_src]
        elif color_count == 1:
            classes['one color'] += [card_src]
        elif color_count == 2:
            classes['two colors'] += [card_src]
        elif color_count == 3:
            classes['three colors'] += [card_src]
        elif color_count == 4:
            classes['four colors'] += [card_src]
        elif color_count == 5:
            classes['five colors'] += [card_src]
        else:
            # Should be unreachable for standard magic colors
            classes['more colors?'] += [card_src]
        
    return classes


def main():
    parser = argparse.ArgumentParser(
        description="""Sorts encoded Magic cards into categories (e.g., by color, type) and formats them for forum posts.

Supports files generated by encode.py with any encoding (std, old, named, etc.).""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile',
                        help='Path to the encoded card file to sort.')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save the output. If not provided, output prints to the console (stdout).')

    # Group: Encoding Options
    enc_group = parser.add_argument_group('Encoding Options')
    enc_group.add_argument('-e', '--encoding', default='std', choices=utils.formats,
                        help="Format of the input data. Match this to the flag used in encode.py (default: 'std').")

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output and progress bars.')
    debug_group.add_argument('-q', '--quiet', action='store_true',
                        help='Suppress all non-error output.')

    args = parser.parse_args()

    # Determine verbose flag (verbose=True unless quiet=True)
    verbose = args.verbose and not args.quiet

    # Determine format ordering based on encoding
    fmt_ordered = cardlib.fmt_ordered_default
    if args.encoding == 'std':
        pass
    elif args.encoding == 'named':
        fmt_ordered = cardlib.fmt_ordered_named
    elif args.encoding == 'noname':
        fmt_ordered = cardlib.fmt_ordered_noname
    elif args.encoding == 'old':
        fmt_ordered = cardlib.fmt_ordered_old
    elif args.encoding == 'norarity':
        fmt_ordered = cardlib.fmt_ordered_norarity
    # For others (vec, rfields), default might not work well, but we'll try default

    if verbose:
        print(f'Opening encoded card file: {args.infile}', file=sys.stderr)
        print(f'Using encoding: {args.encoding}', file=sys.stderr)

    try:
        with open(args.infile, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        print(f"Error reading file {args.infile}: {e}", file=sys.stderr)
        sys.exit(1)

    if not text:
        print("Error: Input file is empty.", file=sys.stderr)
        sys.exit(1)

    # Split by double newline to get individual cards
    cards = text.split('\n\n')
    # Filter empty strings that might result from splitting
    cards = [c for c in cards if c.strip()]

    classes = sortcards(cards, verbose=verbose, fmt_ordered=fmt_ordered)

    outputter = sys.stdout
    ofile = None

    if args.outfile:
        if verbose:
            print(f'Writing output to: {args.outfile}', file=sys.stderr)
        try:
            ofile = open(args.outfile, 'w', encoding='utf-8')
            outputter = ofile
        except Exception as e:
            print(f"Error opening output file {args.outfile}: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        # Print summary (to stderr to separate from data)
        for cardclass, card_list in classes.items():
            if card_list is None:
                if verbose:
                    print(cardclass, file=sys.stderr)
            else:
                if verbose:
                    print(f'  {cardclass}: {len(card_list)}', file=sys.stderr)

        # Write content
        for cardclass, card_list in classes.items():
            if card_list is None:
                outputter.write(f'{cardclass}\n')
            else:
                classlen = len(card_list)
                if classlen > 0:
                    outputter.write(f'[spoiler={cardclass}: {classlen} cards]\n')
                    for card in card_list:
                        outputter.write(f'{card}\n\n')
                    outputter.write('[/spoiler]\n')

    finally:
        if ofile:
            ofile.close()

if __name__ == '__main__':
    main()
