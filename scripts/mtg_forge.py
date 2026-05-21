#!/usr/bin/env python3
import sys
import os
import argparse
import json
import re

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import cardlib

def main():
    parser = argparse.ArgumentParser(
        description="Forge a new Magic card or reforge an existing one from the command line.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Create a card from scratch and view it
  python3 scripts/mtg_forge.py --name "Jules" --cost "{U}{R}" --type "Legendary Creature" --pt "2/2" --text "T: Draw a card." | python3 decode.py

  # Reforge an existing card (requires data/AllPrintings.json)
  python3 scripts/mtg_forge.py --base "Grizzly Bears" --pt "3/3" --name "Super Bears"

  # Create a card and save it to a JSON file
  python3 scripts/mtg_forge.py --name "Test" --type "Instant" --cost "{U}" --text "Counter target spell." --outfile card.json
"""
    )

    # Group: Input / Base
    base_group = parser.add_argument_group('Base Card')
    base_group.add_argument('--base', help='Name of an existing card to use as a template.')
    base_group.add_argument('--infile', default='-',
                            help='Input dataset to search for the base card. Defaults to stdin/AllPrintings.json.')

    # Group: Card Fields
    field_group = parser.add_argument_group('Card Fields')
    field_group.add_argument('-n', '--name', help='Card name.')
    field_group.add_argument('-c', '--cost', help='Mana cost (e.g. "{1}{W}{B}").')
    field_group.add_argument('-t', '--type', help='Full type line (e.g. "Legendary Creature - Human").')
    field_group.add_argument('-x', '--text', help='Rules text (use \\n for newlines).')
    field_group.add_argument('--pt', help='Power/Toughness (e.g. "2/2").')
    field_group.add_argument('--loy', '--loyalty', dest='loy', help='Loyalty or Defense value.')
    field_group.add_argument('-r', '--rarity', help='Rarity (common, uncommon, rare, mythic).')
    field_group.add_argument('--set', help='Set code (e.g. "MOM").')

    # Group: Output Options
    out_group = parser.add_argument_group('Output Options')
    out_group.add_argument('-o', '--outfile', help='Save output to a file instead of printing.')
    out_group.add_argument('--json', action='store_true', help='Output in JSON format (Default).')
    out_group.add_argument('--encoded', action='store_true', help='Output in encoded text format.')
    out_group.add_argument('-S', '--summary', action='store_true', help='Output a one-line summary.')

    # Group: Logging
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')

    args = parser.parse_args()

    # Determine input for base card
    infile = args.infile
    if infile == '-' and sys.stdin.isatty():
        default_data = 'data/AllPrintings.json'
        if os.path.exists(default_data):
            infile = default_data

    card_dict = {}

    if args.base:
        if args.verbose:
            print(f"Searching for base card: {args.base} in {infile}...", file=sys.stderr)

        # Load the base card
        cards = jdecode.mtg_open_file(infile, verbose=args.verbose, grep_name=[f"^{re.escape(args.base)}$"])
        if not cards:
            # Try fuzzy match if exact fails
            cards = jdecode.mtg_open_file(infile, verbose=False, grep_name=[re.escape(args.base)])

        if not cards:
            print(f"Error: Base card '{args.base}' not found.", file=sys.stderr)
            sys.exit(1)

        # Use the first match
        base_card = cards[0]
        card_dict = base_card.to_dict()
        if args.verbose:
            print(f"Using '{base_card.name}' as template.", file=sys.stderr)

    # Apply Overrides
    if args.name: card_dict['name'] = args.name
    if args.cost: card_dict['manaCost'] = args.cost
    if args.type:
        card_dict['type'] = args.type
        # Clear existing split types to allow parse_type_line to re-evaluate
        card_dict.pop('supertypes', None)
        card_dict.pop('types', None)
        card_dict.pop('subtypes', None)

        supertypes, types, subtypes = utils.parse_type_line(args.type)
        if supertypes: card_dict['supertypes'] = supertypes
        if types: card_dict['types'] = types
        if subtypes: card_dict['subtypes'] = subtypes

    if args.text: card_dict['text'] = args.text.replace('\\n', '\n')

    if args.pt:
        if '/' in args.pt:
            p, t = args.pt.split('/', 1)
            card_dict['power'] = p.strip()
            card_dict['toughness'] = t.strip()
        else:
            card_dict['pt'] = args.pt

    if args.loy:
        # Determine if it's a battle or planeswalker
        typeline = card_dict.get('type', '')
        if 'Battle' in typeline:
            card_dict['defense'] = args.loy
        else:
            card_dict['loyalty'] = args.loy

    if args.rarity: card_dict['rarity'] = args.rarity
    if args.set: card_dict['setCode'] = args.set

    # Create a Card object to ensure all internal properties are populated
    # and to support all proyect output formats.
    try:
        # jdecode._normalize_scryfall_card is useful but we built MTGJSON-style
        # Card(card_dict) works best.
        final_card = cardlib.Card(card_dict)
    except Exception as e:
        print(f"Error validating forged card: {e}", file=sys.stderr)
        sys.exit(1)

    # Output
    output_f = open(args.outfile, 'w', encoding='utf-8') if args.outfile else sys.stdout

    try:
        if args.encoded:
            output_f.write(final_card.encode() + '\n')
        elif args.summary:
            # Enable color if output is a TTY
            use_color = sys.stdout.isatty() if not args.outfile else False
            output_f.write(final_card.summary(ansi_color=use_color) + '\n')
        else:
            # Default: JSON
            print(json.dumps(final_card.to_dict(), indent=2), file=output_f)
    finally:
        if args.outfile:
            output_f.close()

if __name__ == "__main__":
    main()
