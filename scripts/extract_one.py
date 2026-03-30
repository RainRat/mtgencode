#!/usr/bin/env python3
"""
This utility extracts a single card object from a large MTGJSON file (like
AllPrintings.json) and saves it to a smaller JSON file. This is useful for
creating targeted test data or debugging specific card processing issues
without having to load the entire dataset.
"""
import sys
import os
import json
import argparse

# Add lib directory to path to access toolkit utilities
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

try:
    import utils
except ImportError:
    # Fallback for when the script is run in environments where lib/ is not available
    class MockUtils:
        class Ansi:
            CYAN = ''
            GREEN = ''
            RED = ''
            BOLD = ''
        @staticmethod
        def colorize(text, color): return text
    utils = MockUtils()

# Try to import tqdm for progress bars
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

def extract_card(input_file, target_set_code, target_card_name, output_file, use_color=False, verbose=False):
    """Loads a JSON file and searches for a specific card across one or all sets."""
    if verbose:
        msg = f"Loading {input_file}... (This may take a moment)"
        if use_color:
            msg = utils.colorize(msg, utils.Ansi.CYAN)
        print(msg, file=sys.stderr)
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            # MTGJSON v4/v5 structure: { "data": { "SET_CODE": { "cards": [ ... ] } } }
            content = json.load(f)
            
        if verbose:
            msg = "File loaded. Searching for card..."
            if use_color:
                msg = utils.colorize(msg, utils.Ansi.CYAN)
            print(msg, file=sys.stderr)

        # Locate the Set
        if 'data' not in content:
            msg = f"Error: 'data' key not found in {input_file}. Is this a valid MTGJSON file?"
            if use_color:
                msg = utils.colorize(msg, utils.Ansi.BOLD + utils.Ansi.RED)
            print(msg, file=sys.stderr)
            return

        # Multi-set search support
        sets_to_search = []
        if target_set_code.upper() in ['ANY', 'ALL', '*']:
            sets_to_search = content['data'].keys()
        elif target_set_code not in content['data']:
            msg = f"Error: Set code '{target_set_code}' not found in file."
            if use_color:
                msg = utils.colorize(msg, utils.Ansi.BOLD + utils.Ansi.RED)
            print(msg, file=sys.stderr)
            return
        else:
            sets_to_search = [target_set_code]

        # Locate the Card
        found_card = None

        # Use tqdm for multi-set searches
        iterable = tqdm(sets_to_search, desc="Searching sets", disable=not (len(sets_to_search) > 1))

        for code in iterable:
            set_data = content['data'][code]
            cards = set_data.get('cards', [])
            for card in cards:
                # Use case-insensitive partial match to find the card
                if target_card_name.lower() in card.get('name', '').lower():
                    found_card = card
                    break
            if found_card:
                break

        # Save the Card
        if found_card:
            found_name = found_card.get('name', 'Unknown')
            msg = f"Found '{found_name}'! Saving to {output_file}..."
            if use_color:
                msg = utils.colorize(msg, utils.Ansi.BOLD + utils.Ansi.GREEN)
            print(msg, file=sys.stderr)

            if output_file == '-':
                json.dump(found_card, sys.stdout, indent=4)
                print()
            else:
                with open(output_file, 'w', encoding='utf-8') as out_f:
                    json.dump(found_card, out_f, indent=4)

            if verbose:
                msg = "Done."
                if use_color:
                    msg = utils.colorize(msg, utils.Ansi.CYAN)
                print(msg, file=sys.stderr)
        else:
            msg = f"Error: Card '{target_card_name}' not found."
            if use_color:
                msg = utils.colorize(msg, utils.Ansi.BOLD + utils.Ansi.RED)
            print(msg, file=sys.stderr)

    except FileNotFoundError:
        msg = f"Error: Could not find {input_file}."
        if use_color:
            msg = utils.colorize(msg, utils.Ansi.BOLD + utils.Ansi.RED)
        print(msg, file=sys.stderr)
    except MemoryError:
        msg = "Error: The file is too large for your RAM."
        if use_color:
            msg = utils.colorize(msg, utils.Ansi.BOLD + utils.Ansi.RED)
        print(msg, file=sys.stderr)
    except json.JSONDecodeError:
        msg = f"Error: {input_file} is not a valid JSON file."
        if use_color:
            msg = utils.colorize(msg, utils.Ansi.BOLD + utils.Ansi.RED)
        print(msg, file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(
        description="Extract a single card from an MTGJSON file.",
        epilog='''
Example Usage:
  python3 scripts/extract_one.py data/AllPrintings.json MOM "Etali, Primal Conqueror"
  python3 scripts/extract_one.py data/AllPrintings.json ANY "Black Lotus" -o lotus.json
  python3 scripts/extract_one.py data/Standard.json LEA "Black Lotus" -o - | jq .

Notes:
  - The card name search is case-insensitive and supports partial matches.
  - Set codes should be uppercase codes (e.g., MOM, LEA).
  - Use 'ANY' or '*' as the set code to search across all sets in the database.
  - Use '-' as the output to print the JSON to stdout for piping.
''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument("input_file", help="Path to the input JSON file (e.g., data/AllPrintings.json).")
    io_group.add_argument("--output", "-o", default="extracted_card.json",
                        help="Path where the extracted card data will be saved. Use '-' for stdout. Default: extracted_card.json")

    # Group: Search Options
    search_group = parser.add_argument_group('Search Options')
    search_group.add_argument("set_code", help="The set code (e.g., MOM, LEA) or 'ANY' to search all sets.")
    search_group.add_argument("card_name", help="The name of the card to extract (supports partial matches).")

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')

    # Color options
    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color output.')

    args = parser.parse_args()

    # Determine if we should use color
    use_color = False
    if args.color is True:
        use_color = True
    elif args.color is None and sys.stderr.isatty():
        use_color = True

    extract_card(args.input_file, args.set_code, args.card_name, args.output, use_color=use_color, verbose=args.verbose or not (args.output == '-'))

if __name__ == "__main__":
    main()
