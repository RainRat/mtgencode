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
from titlecase import titlecase

def get_field_value(card, field, ansi_color=False):
    """Extracts a specific field value from a Card object."""
    field = field.lower().strip()

    if field == 'name':
        res = titlecase(card.name)
        if ansi_color:
            res = utils.colorize(res, card._get_ansi_color())
        return res
    elif field == 'cost':
        return card.cost.format(ansi_color=ansi_color)
    elif field == 'cmc':
        res = str(int(card.cost.cmc)) if card.cost.cmc == int(card.cost.cmc) else f"{card.cost.cmc:.1f}"
        if ansi_color:
            res = utils.colorize(res, utils.Ansi.BOLD + utils.Ansi.GREEN)
        return res
    elif field == 'supertypes':
        return " ".join(card.supertypes)
    elif field == 'types':
        return " ".join(card.types)
    elif field == 'subtypes':
        return " ".join(card.subtypes)
    elif field == 'type':
        res = card.get_type_line(separator=utils.dash_marker)
        if ansi_color:
            res = utils.colorize(res, utils.Ansi.GREEN)
        return res
    elif field == 'pt':
        res = utils.from_unary(card.pt) if card.pt else ""
        if res and ansi_color:
            res = utils.colorize(res, utils.Ansi.RED)
        return res
    elif field == 'power':
        res = utils.from_unary(card.pt_p) if card.pt_p else ""
        if res and ansi_color:
            res = utils.colorize(res, utils.Ansi.RED)
        return res
    elif field == 'toughness':
        res = utils.from_unary(card.pt_t) if card.pt_t else ""
        if res and ansi_color:
            res = utils.colorize(res, utils.Ansi.RED)
        return res
    elif field == 'loyalty':
        res = utils.from_unary(card.loyalty) if card.loyalty else ""
        if res and ansi_color:
            res = utils.colorize(res, utils.Ansi.RED)
        return res
    elif field == 'text':
        return card.get_text(force_unpass=True, ansi_color=ansi_color)
    elif field == 'rarity':
        res = card.rarity_name
        if ansi_color:
            res = utils.colorize(res, utils.Ansi.get_rarity_color(res))
        return res
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
        description="Search card data and extract specific fields. It works with all supported formats (JSON, CSV, XML, or encoded text).",
        epilog='''
Available Fields:
  Basic Metadata:
    name, cost, cmc, rarity, set, number
  Types & Text:
    supertypes, types, subtypes, text, mechanics
  Stats:
    pt (Power/Toughness), power, toughness, loyalty (Loyalty or Defense)
  Color Info:
    identity (Color Identity), id_count
  Simulation & Encoding:
    pack (Pack ID), box (Box ID), encoded (Encoded text string)

Usage Examples:
  # List names and costs of all Goblins in a table
  python3 scripts/mtg_search.py data/AllPrintings.json --grep "Goblin" --fields "name,cost" --table

  # Find all mythic rares with CMC > 7 and save to a JSON file
  python3 scripts/mtg_search.py data/AllPrintings.json --rarity mythic --cmc ">7" --json > mythics.json

  # Generate a Markdown table of legendary creatures for a forum post
  python3 scripts/mtg_search.py data/AllPrintings.json --grep "Legendary" --grep "Creature" --md-table

  # Extract encoded strings for all artifacts from a directory for training
  python3 scripts/mtg_search.py my_data/ --grep-type "Artifact" --fields "encoded"

  # Simulate opening a booster box and list the rare cards in a table
  python3 scripts/mtg_search.py data/AllPrintings.json --box 1 --rarity rare --fields "name,rarity,pack" --table
''' ,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, XML, encoded text, or directory). Defaults to stdin (-).')
    io_group.add_argument('--fields', default='name,cost,cmc,type,pt,rarity',
                        help='Comma-separated list of fields to output (Default: name,cost,cmc,type,pt,rarity).')
    io_group.add_argument('--delimiter', default=' | ',
                        help='The separator used between fields in text output (Default: " | ").')

    # Group: Output Format (Mutually Exclusive)
    fmt_group_title = parser.add_argument_group('Output Format')
    fmt_group = fmt_group_title.add_mutually_exclusive_group()
    fmt_group.add_argument('--text', action='store_true',
                           help='Force plain text output (Default).')
    fmt_group.add_argument('-t', '--table', action='store_true',
                           help='Generate a formatted table for terminal view.')
    fmt_group.add_argument('--md-table', '--mdt', action='store_true',
                           help='Generate a Markdown table.')
    fmt_group.add_argument('-j', '--json', action='store_true',
                           help='Generate a structured JSON file.')
    fmt_group.add_argument('--jsonl', action='store_true',
                           help='Generate a JSON Lines file (one card object per line).')

    # Group: Processing Options
    proc_group = parser.add_argument_group('Processing Options')
    proc_group.add_argument('-n', '--limit', type=int, default=0,
                        help='Only process the first N cards.')
    proc_group.add_argument('--shuffle', action='store_true',
                        help='Shuffle the cards before processing.')
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
                        help='Skip cards matching a search pattern. Use multiple times for OR logic.')
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
                        help='Simulate opening N booster packs and search their contents.')
    filter_group.add_argument('--box', type=int, default=0,
                        help='Simulate opening N booster boxes (36 packs each) and search their contents.')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    debug_group.add_argument('-q', '--quiet', action='store_true', help='Suppress status messages.')

    # Color options
    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None,
                        help='Force enable ANSI color output (useful for piping to less -R).')
    color_group.add_argument('--no-color', action='store_false', dest='color',
                        help='Disable ANSI color output.')

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

    # Set default format if none chosen
    if not (args.text or args.table or args.md_table or args.json or args.jsonl):
        if sys.stdout.isatty():
            args.table = True
        else:
            args.text = True

    # Determine if we should use color
    use_color = False
    if args.color is True:
        use_color = True
    elif args.color is None and not (args.json or args.jsonl or args.md_table) and sys.stdout.isatty():
        use_color = True

    # Process output
    field_list = [f.strip() for f in args.fields.split(',')]

    if args.json:
        results = []
        for card in cards:
            card_data = {}
            for field in field_list:
                card_data[field] = get_field_value(card, field, ansi_color=use_color)
            results.append(card_data)
        print(json.dumps(results, indent=2))
    elif args.jsonl:
        for card in cards:
            card_data = {}
            for field in field_list:
                card_data[field] = get_field_value(card, field, ansi_color=use_color)
            print(json.dumps(card_data))
    elif args.table or args.md_table:
        import datalib
        rows = []
        # Header
        header = [f.title() for f in field_list]
        if use_color:
            header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]
        rows.append(header)

        # Content
        for card in cards:
            row = [get_field_value(card, f, ansi_color=use_color) for f in field_list]
            rows.append(row)

        if args.md_table:
            # Markdown table output
            header_row = "| " + " | ".join(header) + " |"
            # Alignment row
            align_row = "|"
            for field in field_list:
                if field.lower() in ['cmc', 'id_count', 'power', 'toughness', 'loyalty', 'pack', 'box']:
                    align_row += " ---: |"
                else:
                    align_row += " :--- |"
            print(header_row)
            print(align_row)
            for row in rows[1:]:
                # Escape pipes in markdown
                escaped_row = [str(cell).replace('|', '\\|').replace('\n', ' ') for cell in row]
                print("| " + " | ".join(escaped_row) + " |")
        else:
            # Terminal table output
            header_text = "SEARCH RESULTS"
            if use_color:
                print(utils.colorize(header_text, utils.Ansi.BOLD + utils.Ansi.CYAN + utils.Ansi.UNDERLINE))
            else:
                print(header_text)
                print("=" * len(header_text))

            aligns = []
            for field in field_list:
                if field.lower() in ['cmc', 'id_count', 'power', 'toughness', 'loyalty', 'pack', 'box']:
                    aligns.append('r')
                else:
                    aligns.append('l')

            # Add separator row
            col_widths = datalib.get_col_widths(rows)
            separator = ['-' * w for w in col_widths]
            rows.insert(1, separator)

            for row in datalib.padrows(rows, aligns=aligns):
                print("  " + row)
    else: # Default text output
        for card in cards:
            card_data = [get_field_value(card, f, ansi_color=use_color) for f in field_list]
            print(args.delimiter.join(str(val) for val in card_data))

    if not args.quiet:
        utils.print_operation_summary("Search", len(cards), 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
