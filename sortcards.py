#!/usr/bin/env python3
import sys
import argparse
from collections import OrderedDict

# Try to import tqdm for progress bars
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

def sortcards(cards, verbose=False):
    """
    Sorts a list of encoded card strings into various categories.
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
        # special classes
        if '|\n|' in card:
            classes['multicards'] += [card.replace('|\n|', '|\n~~~~~~~~~~~~~~~~\n|')]
            continue
        
        # inclusive classes
        if 'X' in card:
            classes['X cards'] += [card]
        if 'kick' in card:
            classes['kicker cards'] += [card]
        if '%' in card or '#' in card:
            classes['counter cards'] += [card]
        if 'uncast' in card:
            classes['uncast cards'] += [card]
        if '[' in card or ']' in card or '=' in card:
            classes['choice cards'] += [card]
        if '|equipment|' in card or 'equip {' in card:
            classes['equipment'] += [card]
        if 'level up' in card or 'level &' in card:
            classes['levelers'] += [card]
        if '|legendary|' in card:
            classes['legendary'] += [card]

        # exclusive classes
        if '|battle|' in card:
            classes['battles'] += [card]
        elif '|planeswalker|' in card:
            classes['planeswalkers'] += [card]
        elif '|land|' in card:
            classes['lands'] += [card]
        elif '|instant|' in card:
            classes['instants'] += [card]
        elif '|sorcery|' in card:
            classes['sorceries'] += [card]
        elif '|enchantment|' in card:
            classes['enchantments'] += [card]
        elif '|artifact|' in card:
            classes['noncreature artifacts'] += [card]
        elif '|creature|' in card or 'artifact creature' in card:
            classes['creatures'] += [card]
        else:
            classes['other'] += [card]

        # color classes need to find the mana cost
        fields = card.split('|')
        if len(fields) != 11:
            classes['unknown color'] += [card]
        else:
            cost = fields[8]
            color_count = 0
            if 'W' in cost or 'U' in cost or 'B' in cost or 'R' in cost or 'G' in cost:
                if 'W' in cost:
                    classes['white'] += [card]
                    color_count += 1
                if 'U' in cost:
                    classes['blue'] += [card]
                    color_count += 1
                if 'B' in cost:
                    classes['black'] += [card]
                    color_count += 1
                if 'R' in cost:
                    classes['red'] += [card]
                    color_count += 1
                if 'G' in cost:
                    classes['green'] += [card]
                    color_count += 1
                # should be unreachable
                if color_count == 0:
                    classes['unknown color'] += [card]
            else:
                if '|land|' in card:
                    classes['colorless land'] += [card]
                else:
                    classes['colorless nonland'] += [card]
            
            if color_count == 0:
                classes['zero colors'] += [card]
            elif color_count == 1:
                classes['one color'] += [card]
            elif color_count == 2:
                classes['two colors'] += [card]
            elif color_count == 3:
                classes['three colors'] += [card]
            elif color_count == 4:
                classes['four colors'] += [card]
            elif color_count == 5:
                classes['five colors'] += [card]
            else:
                classes['6+ colors'] += [card]
        
    return classes


def main():
    parser = argparse.ArgumentParser(
        description="""Sorts encoded Magic cards into categories (e.g., by color, type) and formats them for forum posts.

IMPORTANT: This tool requires a specific input format.
You must generate your input file using: encode.py --encoding old""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile',
                        help='Path to the encoded card file to sort. Requires "old" encoding.')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save the output. If not provided, output prints to the console (stdout).')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output and progress bars.')
    debug_group.add_argument('-q', '--quiet', action='store_true',
                        help='Suppress all non-error output.')

    args = parser.parse_args()

    # Determine verbose flag (verbose=True unless quiet=True)
    verbose = args.verbose and not args.quiet

    if verbose:
        print(f'Opening encoded card file: {args.infile}', file=sys.stderr)

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
    if len(cards) > 2:
        # Standard format usually has partial/empty entries at start/end
        cards = cards[1:-1]
    else:
        # Fallback if the file structure is different than expected
        cards = [c for c in cards if c.strip()]

    classes = sortcards(cards, verbose=verbose)

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
