#!/usr/bin/env python3
import sys
import os
import argparse
import difflib
import re

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import cardlib

def main():
    parser = argparse.ArgumentParser(
        description="Search and display card details in a human-readable format. "
                    "Optimized for quick lookup with fuzzy name matching.",
        epilog='''
Example Usage:
  # Lookup a specific card by name
  python3 scripts/mtg_oracle.py data/AllPrintings.json "Grizzly Bears"

  # Find all rares in a set matching a keyword
  python3 scripts/mtg_oracle.py data/AllPrintings.json --set MOM --rarity rare --grep "Battle"

  # Use fuzzy matching for misspelled names
  python3 scripts/mtg_oracle.py data/AllPrintings.json "Grizly Beers"
''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, encoded text, or directory). Defaults to stdin (-).')
    io_group.add_argument('query', nargs='?', default=None,
                        help='Card name to look up. Supports fuzzy matching if no exact match is found.')

    # Group: Content Formatting
    enc_group = parser.add_argument_group('Content Formatting')
    enc_group.add_argument('--gatherer', action='store_true',
                        help='Use modern Gatherer-style wording and formatting.')
    enc_group.add_argument('--nolabel', action='store_true',
                        help="Input file does not have field labels (like '|cost|' or '|text|').")
    enc_group.add_argument('--nolinetrans', action='store_true',
                        help='Input file does not use automatic line reordering.')

    # Group: Filtering Options (Standard across tools)
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('--grep', action='append',
                        help='Only include cards matching a search pattern (checks name, typeline, text, cost, and stats). Use multiple times for AND logic.')
    filter_group.add_argument('--vgrep', '--exclude', action='append',
                        help='Skip cards matching a search pattern (checks name, typeline, text, cost, and stats). Use multiple times for OR logic.')
    filter_group.add_argument('--set', action='append',
                        help='Only include cards from specific sets.')
    filter_group.add_argument('--rarity', action='append',
                        help="Only include cards of specific rarities. Supports full names (e.g., 'common', 'mythic') or shorthands: O (Common), N (Uncommon), A (Rare), Y (Mythic), I (Special), L (Basic Land). Supports multiple values (OR logic).")
    filter_group.add_argument('--colors', action='append',
                        help="Only include cards of specific colors (W, U, B, R, G). Use 'C' or 'A' for colorless. Supports multiple values (OR logic).")
    filter_group.add_argument('--identity', action='append',
                        help="Only include cards with specific colors in their color identity (W, U, B, R, G). Use 'C' or 'A' for colorless. Supports multiple values (OR logic).")
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
                        help='Filter cards using a standard MTG decklist file.')

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

    # Load and filter cards
    cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose,
                                  linetrans=not args.nolinetrans,
                                  fmt_labeled=None if args.nolabel else cardlib.fmt_labeled_default,
                                  grep=args.grep, vgrep=args.vgrep,
                                  sets=args.set, rarities=args.rarity,
                                  colors=args.colors, cmcs=args.cmc,
                                  pows=args.pow, tous=args.tou, loys=args.loy,
                                  mechanics=args.mechanic,
                                  identities=args.identity,
                                  decklist_file=args.deck)

    if not cards:
        if not args.quiet:
            print("No cards found matching the criteria.", file=sys.stderr)
        return

    # If query is provided, perform name-based filtering
    if args.query:
        # Sanitize query to match internal representations (hyphens are dash_marker)
        query_sanitized = args.query.lower().replace('-', utils.dash_marker)
        query_lower = args.query.lower()
        exact_matches = [c for c in cards if c.name.lower() == query_sanitized]

        if exact_matches:
            display_cards = exact_matches
        else:
            # Fallback to partial matches
            partial_matches = [c for c in cards if query_lower in c.name.lower()]
            if partial_matches:
                display_cards = partial_matches
            else:
                # Fallback to fuzzy suggestions
                # Build a mapping of searchable names (full names and significant words)
                # to the actual card objects for suggesting and matching.
                search_map = {}
                for c in cards:
                    unpassed_name = c.name.replace(utils.dash_marker, '-')
                    search_map[c.name.lower()] = cardlib.titlecase(unpassed_name)
                    for word in unpassed_name.split():
                        if len(word) > 3:
                            # Strip punctuation for word-based fuzzy matching
                            clean_word = re.sub(r'[^a-zA-Z0-9]', '', word).lower()
                            if clean_word and clean_word not in search_map:
                                search_map[clean_word] = cardlib.titlecase(unpassed_name)

                matches = difflib.get_close_matches(query_lower, list(search_map.keys()), n=3, cutoff=0.7)

                if not args.quiet:
                    print(f"Card '{args.query}' not found.")
                    if matches:
                        print("Did you mean:")
                        seen_suggestions = set()
                        for m in matches:
                            suggestion = search_map[m]
                            if suggestion not in seen_suggestions:
                                print(f"  - {suggestion}")
                                seen_suggestions.add(suggestion)
                return
    else:
        display_cards = cards

    # Display the cards
    for i, card in enumerate(display_cards):
        if i > 0:
            print("\n" + "=" * 40 + "\n")

        print(card.format(gatherer=args.gatherer, ansi_color=use_color))

    if not args.quiet and len(display_cards) > 1:
        summary = f"\nShowing {len(display_cards)} matches."
        if use_color:
            summary = utils.colorize(summary, utils.Ansi.BOLD + utils.Ansi.CYAN)
        print(summary, file=sys.stderr)

if __name__ == "__main__":
    main()
