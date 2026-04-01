#!/usr/bin/env python3
import sys
import os
import argparse
import json

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import cardlib

def get_field_value(card, field):
    """Extracts a specific field value from a Card object."""
    field = field.lower().strip()

    if field == 'name':
        return card.name
    elif field == 'cost':
        return card.cost.format()
    elif field == 'cmc':
        return card.cost.cmc
    elif field == 'supertypes':
        return " ".join(card.supertypes)
    elif field == 'types':
        return " ".join(card.types)
    elif field == 'subtypes':
        return " ".join(card.subtypes)
    elif field == 'pt':
        return utils.from_unary(card.pt) if card.pt else ""
    elif field == 'loyalty':
        return utils.from_unary(card.loyalty) if card.loyalty else ""
    elif field == 'text':
        return card.get_text(force_unpass=True)
    elif field == 'rarity':
        return card.rarity_name
    elif field == 'mechanics':
        return ", ".join(sorted(list(card.mechanics)))
    elif field == 'identity':
        return card.color_identity
    elif field == 'id_count':
        return len(card.color_identity)
    elif field == 'set':
        return card.set_code if card.set_code else ""
    elif field == 'number':
        return card.number if card.number else ""
    elif field == 'pack':
        return getattr(card, 'pack_id', "")
    elif field == 'box':
        return getattr(card, 'box_id', "")
    elif field == 'encoded':
        return card.encode()
    else:
        return ""

def main():
    parser = argparse.ArgumentParser(
        description="Search Magic: The Gathering card data and extract specific fields.",
        epilog='''
Available Fields:
  name, cost, cmc, supertypes, types, subtypes, pt, loyalty,
  text, rarity, mechanics, identity, id_count, set, number,
  pack, box, encoded

Example Usage:
  # List names and costs of all Goblins
  python3 scripts/mtg_search.py data/AllPrintings.json --grep "Goblin" --fields "name,cost"

  # Find all mythic rares with CMC > 7 and output as JSON
  python3 scripts/mtg_search.py data/AllPrintings.json --rarity mythic --cmc ">7" --json

  # Extract encoded strings for all artifacts from a directory
  python3 scripts/mtg_search.py my_data/ --grep-type "Artifact" --fields "encoded"
''' ,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, XML, encoded text, or directory). Defaults to stdin (-).')
    io_group.add_argument('--fields', default='name',
                        help='Comma-separated list of fields to output (Default: name).')
    io_group.add_argument('--delimiter', default=' | ',
                        help='Separator between fields in text output (Default: " | ").')
    io_group.add_argument('--json', action='store_true',
                        help='Output results as a JSON list of objects.')

    # Group: Processing Options
    proc_group = parser.add_argument_group('Processing Options')
    proc_group.add_argument('-n', '--limit', type=int, default=0,
                        help='Only process the first N cards.')
    proc_group.add_argument('--shuffle', action='store_true',
                        help='Randomize the order of cards.')
    proc_group.add_argument('--sample', type=int, default=0,
                        help='Pick N random cards (shorthand for --shuffle --limit N).')
    proc_group.add_argument('--sort', choices=['name', 'color', 'identity', 'type', 'cmc', 'rarity', 'power', 'toughness', 'loyalty', 'set'],
                        help='Sort cards by a specific criterion.')

    # Group: Filtering Options (Standard across tools)
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('--grep', action='append',
                        help='Only include cards matching a search pattern (checks name, type, and text). Use multiple times for AND logic.')
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
                        help='Exclude cards matching a search pattern. Use multiple times for OR logic.')
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
                        help='Only include cards from specific sets.')
    filter_group.add_argument('--rarity', action='append',
                        help='Only include cards of specific rarities.')
    filter_group.add_argument('--colors', action='append',
                        help='Only include cards of specific colors.')
    filter_group.add_argument('--identity', action='append',
                        help='Only include cards with specific color identities.')
    filter_group.add_argument('--id-count', action='append',
                        help='Only include cards with specific color identity counts.')
    filter_group.add_argument('--cmc', action='append',
                        help='Only include cards with specific CMC values.')
    filter_group.add_argument('--pow', '--power', action='append', dest='pow',
                        help='Only include cards with specific Power values.')
    filter_group.add_argument('--tou', '--toughness', action='append', dest='tou',
                        help='Only include cards with specific Toughness values.')
    filter_group.add_argument('--loy', '--loyalty', '--defense', action='append', dest='loy',
                        help='Only include cards with specific Loyalty or Defense values.')
    filter_group.add_argument('--mechanic', action='append',
                        help='Only include cards with specific mechanical features.')
    filter_group.add_argument('--deck-filter', '--decklist-filter', dest='deck',
                        help='Filter cards using a standard MTG decklist file.')
    filter_group.add_argument('--booster', type=int, default=0,
                        help='Simulate opening N booster packs.')
    filter_group.add_argument('--box', type=int, default=0,
                        help='Simulate opening N booster boxes (36 packs each).')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    debug_group.add_argument('-q', '--quiet', action='store_true', help='Suppress status messages.')

    args = parser.parse_args()

    # Handle --sample
    if args.sample > 0:
        args.shuffle = True
        args.limit = args.sample

    # Load and filter cards
    cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose,
                                  grep=args.grep, vgrep=args.vgrep,
                                  grep_name=args.grep_name, vgrep_name=args.exclude_name,
                                  grep_types=args.grep_type, vgrep_types=args.exclude_type,
                                  grep_text=args.grep_text, vgrep_text=args.exclude_text,
                                  grep_cost=args.grep_cost, vgrep_cost=args.exclude_cost,
                                  grep_pt=args.grep_pt, vgrep_pt=args.exclude_pt,
                                  grep_loyalty=args.grep_loyalty, vgrep_loyalty=args.exclude_loyalty,
                                  sets=args.set, rarities=args.rarity,
                                  colors=args.colors, cmcs=args.cmc,
                                  pows=args.pow, tous=args.tou, loys=args.loy,
                                  mechanics=args.mechanic,
                                  identities=args.identity, id_counts=args.id_count,
                                  decklist_file=args.deck,
                                  booster=args.booster, box=args.box,
                                  shuffle=args.shuffle)

    if args.sort:
        import sortlib
        cards = sortlib.sort_cards(cards, args.sort, quiet=args.quiet)

    if args.limit > 0:
        cards = cards[:args.limit]

    # Process output
    field_list = [f.strip() for f in args.fields.split(',')]

    results = []
    for card in cards:
        card_data = {}
        for field in field_list:
            card_data[field] = get_field_value(card, field)
        results.append(card_data)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for card_data in results:
            output_line = args.delimiter.join(str(card_data[f]) for f in field_list)
            print(output_line)

    if not args.quiet:
        utils.print_operation_summary("Search", len(cards), 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
