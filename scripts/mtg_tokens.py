#!/usr/bin/env python3
import sys
import os
import argparse
import json
import re
from collections import OrderedDict

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import datalib

def extract_tokens_from_text(text):
    """
    Extracts token properties from a rules text string.
    Returns a list of token dictionaries.
    """
    found_tokens = []

    # Clean text: lower case and standard whitespace
    text = text.replace('\n', ' ').strip()

    # 1. Standard Creature Token Pattern:
    # "Create [a|N] [P/T] [color(s)] [type(s)] [creature] token[s] [with [abilities]]"
    # Examples:
    # "Create a 1/1 white Soldier creature token."
    # "Create two 2/2 black Zombie creature tokens."
    # "Create a 3/3 green Beast creature token with trample."
    creature_token_regex = r"(?:[Cc]reate)\s+(?:[Aa]n?|two|three|four|five|X)\s+([0-9/X+&^]+)\s+([a-zA-Z\s,]+)\s+token[s]?(?:\s+with\s+([^,.]+))?"

    for match in re.finditer(creature_token_regex, text):
        pt = match.group(1)
        # Attempt to split color and types from the second group
        # This is a bit heuristic
        color_and_types = match.group(2).strip()
        abilities = match.group(3).strip() if match.group(3) else ""

        # Strip trailing 'creature' if present
        if color_and_types.lower().endswith(' creature'):
            color_and_types = color_and_types[:-9]

        # Basic color extraction
        colors = []
        for c in ['white', 'blue', 'black', 'red', 'green', 'colorless']:
            if c in color_and_types.lower():
                colors.append(c.capitalize())

        # Remaining parts are likely types
        # This is very simplified but works for standard tokens
        types = color_and_types
        for c in ['white', 'blue', 'black', 'red', 'green', 'colorless', 'multi']:
             types = re.sub(c, '', types, flags=re.IGNORECASE)
        types = " ".join([t.capitalize() for t in types.split()])

        # Final name construction
        display_name = f"{pt} {', '.join(colors) if colors else 'Colorless'} {types} Token".strip()

        token = {
            'name': display_name,
            'pt': pt,
            'color': ", ".join(colors) if colors else "Colorless",
            'type': f"{types} Creature".strip(),
            'abilities': abilities,
            'source_text': match.group(0)
        }
        found_tokens.append(token)

    # 2. Named/Predefined Token Pattern:
    # "Create [a|N] [Name] token[s]" (where Name is Treasure, Food, Clue, etc.)
    # Examples:
    # "Create a Treasure token."
    # "Create two Food tokens."
    named_tokens = ['Treasure', 'Food', 'Clue', 'Blood', 'Map', 'Role', 'Incubator', 'Powerstone', 'Walker']
    named_token_regex = r"(?:[Cc]reate)\s+(?:[Aa]n?|two|three|four|five|X)\s+(" + "|".join(named_tokens) + r")\s+token[s]?"

    for match in re.finditer(named_token_regex, text, re.IGNORECASE):
        name = match.group(1).capitalize()

        # Predefined properties for common tokens
        token = {
            'name': f"{name} Token",
            'pt': "",
            'color': "Colorless",
            'type': name,
            'abilities': "",
            'source_text': match.group(0)
        }

        # Add special properties for common ones
        if name == 'Treasure':
            token['type'] = 'Artifact'
            token['abilities'] = "{T}, Sacrifice this artifact: Add one mana of any color."
        elif name == 'Food':
            token['type'] = 'Artifact'
            token['abilities'] = "{2}, {T}, Sacrifice this artifact: You gain 3 life."
        elif name == 'Clue':
            token['type'] = 'Artifact'
            token['abilities'] = "{2}, Sacrifice this artifact: Draw a card."

        found_tokens.append(token)

    return found_tokens

def main():
    parser = argparse.ArgumentParser(
        description="Extract and summarize token definitions from Magic: The Gathering rules text.",
        epilog='''
Example Usage:
  # List all tokens found in a specific set
  python3 scripts/mtg_tokens.py data/AllPrintings.json --set MOM

  # Export all token definitions to a JSON file
  python3 scripts/mtg_tokens.py data/AllPrintings.json --json > tokens.json
''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, encoded text, etc.). Defaults to stdin (-).')
    io_group.add_argument('--json', action='store_true',
                        help='Output token definitions in JSON format.')

    # Group: Filtering Options (Standard across tools)
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('--grep', action='append',
                        help='Only include cards matching a search pattern (checks name, typeline, text, cost, and stats). Use multiple times for AND logic.')
    filter_group.add_argument('--set', action='append',
                        help='Only include cards from specific sets (e.g., MOM, MRD). Supports multiple sets (OR logic).')
    filter_group.add_argument('--rarity', action='append',
                        help="Only include cards of specific rarities. Supports full names (e.g., 'common', 'mythic') or shorthands: O (Common), N (Uncommon), A (Rare), Y (Mythic), I (Special), L (Basic Land). Supports multiple values (OR logic).")

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    debug_group.add_argument('-q', '--quiet', action='store_true', help='Suppress status messages.')

    # Color options
    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color output.')

    args = parser.parse_args()

    # Determine if we should use color
    use_color = False
    if args.color is True:
        use_color = True
    elif args.color is None and sys.stdout.isatty():
        use_color = True

    # Load cards
    cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose,
                                  grep=args.grep, sets=args.set, rarities=args.rarity)

    if not cards:
        if not args.quiet:
            print("No cards found matching the criteria.", file=sys.stderr)
        return

    # Extract tokens from all cards
    all_tokens = []
    for card in cards:
        text = card.get_text(force_unpass=True)
        if args.verbose:
            print(f"Processing card: {card.name}")
            print(f"Text: {text}")
        found = extract_tokens_from_text(text)
        if args.verbose:
            print(f"Found {len(found)} tokens.")
        for t in found:
            # Attach source card info for reference
            t['source_card'] = card.name
            all_tokens.append(t)

    # De-duplicate tokens based on properties (excluding source card)
    unique_tokens = OrderedDict()
    for t in all_tokens:
        # Create a key based on core properties
        key = (t['pt'], t['color'], t['type'], t['abilities'])
        if key not in unique_tokens:
            unique_tokens[key] = t
            unique_tokens[key]['count'] = 1
            unique_tokens[key]['sources'] = [t['source_card']]
        else:
            unique_tokens[key]['count'] += 1
            if t['source_card'] not in unique_tokens[key]['sources']:
                unique_tokens[key]['sources'].append(t['source_card'])

    token_list = list(unique_tokens.values())
    # Sort by name
    token_list.sort(key=lambda x: x['name'])

    if args.json:
        # Clean up for JSON output
        for t in token_list:
            if 'source_text' in t:
                del t['source_text']
            if 'source_card' in t:
                del t['source_card']
        print(json.dumps(token_list, indent=2))
    else:
        if not token_list:
            print("No token definitions found in rules text.")
            return

        utils.print_header("EXTRACTED TOKENS", count=len(token_list), use_color=use_color)

        header = ["Token Name", "P/T", "Color", "Type", "Abilities", "Count"]
        if use_color:
            header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

        rows = [header]
        for t in token_list:
            name = t['name']
            pt = t['pt']
            color = t['color']
            stype = t['type']
            abilities = t['abilities']
            count = str(t['count'])

            if use_color:
                name = utils.colorize(name, utils.Ansi.BOLD + utils.Ansi.CYAN)
                pt = utils.colorize(pt, utils.Ansi.RED)
                # Colorize color name if single
                if ',' not in color and color != 'Colorless':
                    color = utils.colorize(color, utils.Ansi.get_color_color(color[0]))
                stype = utils.colorize(stype, utils.Ansi.GREEN)
                count = utils.colorize(count, utils.Ansi.BOLD + utils.Ansi.GREEN)

            rows.append([name, pt, color, stype, abilities, count])

        datalib.add_separator_row(rows)

        datalib.printrows(datalib.padrows(rows, aligns=['l', 'r', 'l', 'l', 'l', 'r']), indent=2)

        if not args.quiet:
            summary = f"\nSuccessfully extracted {len(token_list)} unique token types from {len(cards)} cards."
            if use_color:
                summary = utils.colorize(summary, utils.Ansi.BOLD + utils.Ansi.GREEN)
            print(summary, file=sys.stderr)

if __name__ == "__main__":
    main()
