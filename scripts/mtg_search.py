#!/usr/bin/env python3
import sys
import os
import argparse
import json
import csv

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
from titlecase import titlecase

# Metadata mapping for available fields: Pretty headers, alignment, and aliases
FIELD_MAP = {
    'name': {'header': 'Name', 'align': 'l', 'aliases': []},
    'cost': {'header': 'Cost', 'align': 'l', 'aliases': ['mana', 'mana_cost', 'manacost']},
    'cmc': {'header': 'CMC', 'align': 'r', 'aliases': ['mv', 'mana_value']},
    'colors': {'header': 'Colors', 'align': 'l', 'aliases': []},
    'type': {'header': 'Type', 'align': 'l', 'aliases': ['typeline']},
    'supertypes': {'header': 'Supertypes', 'align': 'l', 'aliases': []},
    'types': {'header': 'Types', 'align': 'l', 'aliases': []},
    'subtypes': {'header': 'Subtypes', 'align': 'l', 'aliases': []},
    'pt': {'header': 'P/T', 'align': 'r', 'aliases': ['pow_tou']},
    'stats': {'header': 'Stats', 'align': 'r', 'aliases': []},
    'power': {'header': 'Power', 'align': 'r', 'aliases': ['pow']},
    'toughness': {'header': 'Toughness', 'align': 'r', 'aliases': ['tou']},
    'loyalty': {'header': 'Loyalty', 'align': 'r', 'aliases': ['loy', 'defense', 'def']},
    'text': {'header': 'Rules Text', 'align': 'l', 'aliases': ['oracle', 'rules']},
    'rarity': {'header': 'Rarity', 'align': 'l', 'aliases': []},
    'mechanics': {'header': 'Mechanics', 'align': 'l', 'aliases': ['keywords']},
    'identity': {'header': 'Identity', 'align': 'l', 'aliases': ['color_identity', 'ci']},
    'id_count': {'header': 'ID', 'align': 'r', 'aliases': ['identity_count']},
    'set': {'header': 'Set', 'align': 'l', 'aliases': ['code']},
    'number': {'header': 'Num', 'align': 'r', 'aliases': ['collector_number', 'num']},
    'pack': {'header': 'Pack', 'align': 'r', 'aliases': ['pack_id']},
    'box': {'header': 'Box', 'align': 'r', 'aliases': ['box_id']},
    'encoded': {'header': 'Encoded', 'align': 'l', 'aliases': []},
}

def get_field_canonical_name(field):
    """Maps a field alias to its canonical name."""
    f = field.lower().strip()
    if f in FIELD_MAP:
        return f
    for k, v in FIELD_MAP.items():
        if f in v.get('aliases', []):
            return k
    return f

def get_field_value(card, field, ansi_color=False):
    """Extracts a specific field value from a Card object, recursing for b-sides."""
    canon = get_field_canonical_name(field)

    res = ""
    if canon == 'name':
        res = titlecase(card.name)
        if ansi_color:
            res = utils.colorize(res, card._get_ansi_color())
    elif canon == 'cost':
        res = card.cost.format(ansi_color=ansi_color)
    elif canon == 'cmc':
        res = str(int(card.cost.cmc)) if card.cost.cmc == int(card.cost.cmc) else f"{card.cost.cmc:.1f}"
        if ansi_color:
            res = utils.colorize(res, utils.Ansi.BOLD + utils.Ansi.GREEN)
    elif canon == 'colors':
        res = "".join(card.cost.colors)
        if ansi_color and res:
            res = "".join([utils.colorize(c, utils.Ansi.get_color_color(c)) for c in res])
    elif canon == 'supertypes':
        res = " ".join(card.supertypes)
    elif canon == 'types':
        res = " ".join(card.types)
    elif canon == 'subtypes':
        res = " ".join(card.subtypes)
    elif canon == 'type':
        res = card.get_type_line(separator=utils.dash_marker)
        if ansi_color:
            res = utils.colorize(res, utils.Ansi.GREEN)
    elif canon == 'pt':
        res = utils.from_unary(card.pt) if card.pt else ""
        if res and ansi_color:
            res = utils.colorize(res, utils.Ansi.RED)
    elif canon == 'stats':
        # Smart field that pulls P/T, Loyalty, or Defense
        res = utils.from_unary(card.pt) if card.pt else ""
        if not res:
            res = utils.from_unary(card.loyalty) if card.loyalty else ""
        if res and ansi_color:
            res = utils.colorize(res, utils.Ansi.RED)
    elif canon == 'power':
        res = utils.from_unary(card.pt_p) if card.pt_p else ""
        if res and ansi_color:
            res = utils.colorize(res, utils.Ansi.RED)
    elif canon == 'toughness':
        res = utils.from_unary(card.pt_t) if card.pt_t else ""
        if res and ansi_color:
            res = utils.colorize(res, utils.Ansi.RED)
    elif canon == 'loyalty':
        res = utils.from_unary(card.loyalty) if card.loyalty else ""
        if res and ansi_color:
            res = utils.colorize(res, utils.Ansi.RED)
    elif canon == 'text':
        res = card.get_text(force_unpass=True, ansi_color=ansi_color)
    elif canon == 'rarity':
        res = card.rarity_name
        if ansi_color and res:
            res = utils.colorize(res, utils.Ansi.get_rarity_color(res))
    elif canon == 'mechanics':
        # mechanics and identity properties already aggregate b-sides
        return ", ".join(sorted(list(card.mechanics)))
    elif canon == 'identity':
        res = card.color_identity
        if ansi_color and res:
            res = "".join([utils.colorize(c, utils.Ansi.get_color_color(c)) for c in res])
        return res
    elif canon == 'id_count':
        res = len(card.color_identity)
        if ansi_color:
            res = utils.colorize(str(res), utils.Ansi.BOLD + utils.Ansi.YELLOW)
        return str(res)
    elif canon == 'set':
        return card.set_code if card.set_code else ""
    elif canon == 'number':
        return card.number if card.number else ""
    elif canon == 'pack':
        return str(getattr(card, 'pack_id', ""))
    elif canon == 'box':
        return str(getattr(card, 'box_id', ""))
    elif canon == 'encoded':
        res = card.encode()
    else:
        return ""

    # Recursive joining for multi-faced cards
    if card.bside:
        # Exclude fields that are typically shared or already aggregated
        if canon in ['rarity', 'set', 'pack', 'box', 'id_count', 'identity', 'mechanics']:
            return str(res)

        b_res = get_field_value(card.bside, field, ansi_color)
        if res and b_res:
            sep = "\n\n" if canon in ['text', 'encoded'] else " // "
            return f"{res}{sep}{b_res}"
        return str(res or b_res)

    return str(res)

def main():
    parser = argparse.ArgumentParser(
        description="Search card data and extract specific fields. It works with all supported formats (JSON, CSV, XML, or encoded text).",
        epilog='''
Available Fields (aliases in parentheses):
  Basic Metadata:
    name, cost (mana), cmc (mv), rarity, set (code), number (num)
  Types & Text:
    type (typeline), text (rules), mechanics (keywords), supertypes, types, subtypes
  Stats:
    stats (Smart P/T or Loyalty), pt, power (pow), toughness (tou), loyalty (def)
  Color Info:
    colors, identity (ci), id_count
  Simulation & Encoding:
    pack, box, encoded

Usage Examples:
  # List names and costs of all Goblins in a table
  python3 scripts/mtg_search.py data/AllPrintings.json --grep "Goblin" --fields "name,cost" --table

  # Find all mythic rares with CMC > 7 and save to a JSON file
  python3 scripts/mtg_search.py data/AllPrintings.json --rarity mythic --cmc ">7" mythics.json

  # Export all legendary creatures to a CSV file
  python3 scripts/mtg_search.py data/AllPrintings.json --grep "Legendary" --grep "Creature" --fields "name,mana,type,stats,rarity" legends.csv
''' ,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (MTGJSON, Scryfall, CSV, XML, MSE, JSONL, ZIP, or Decklist), encoded text, or directory. Defaults to stdin (-).')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save the search results. If not provided, results print to the console. The format is automatically detected from the file extension.')
    io_group.add_argument('--fields', default='name,cost,cmc,type,stats,rarity,mechanics',
                        help='Comma-separated list of fields to output (Default: name,cost,cmc,type,stats,rarity,mechanics).')
    io_group.add_argument('--delimiter', default=' | ',
                        help='The separator used between fields in text output (Default: " | ").')

    # Group: Output Format (Mutually Exclusive)
    fmt_group_title = parser.add_argument_group('Output Format')
    fmt_group = fmt_group_title.add_mutually_exclusive_group()
    fmt_group.add_argument('--text', action='store_true',
                           help='Force plain text output (Default unless detected from extension).')
    fmt_group.add_argument('-t', '--table', action='store_true',
                           help='Generate a formatted table for terminal view (Auto-detected for .tbl or .table).')
    fmt_group.add_argument('--md-table', '--mdt', action='store_true',
                           help='Generate a Markdown table (Auto-detected for .md or .mdt).')
    fmt_group.add_argument('-j', '--json', action='store_true',
                           help='Generate a structured JSON file (Auto-detected for .json).')
    fmt_group.add_argument('--jsonl', action='store_true',
                           help='Generate a JSON Lines file (one card object per line). Auto-detected for .jsonl.')
    fmt_group.add_argument('--csv', action='store_true',
                           help='Generate a CSV file (Auto-detected for .csv).')

    # Group: Processing Options
    proc_group = parser.add_argument_group('Processing Options')
    proc_group.add_argument('-n', '--limit', type=int, default=0,
                        help='Only process the first N cards.')
    proc_group.add_argument('--shuffle', action='store_true',
                        help='Shuffle the cards before processing.')
    proc_group.add_argument('--sample', type=int, default=0,
                        help='Pick N random cards (shorthand for --shuffle --limit N).')
    proc_group.add_argument('--sort', choices=['name', 'color', 'identity', 'type', 'cmc', 'rarity', 'power', 'toughness', 'loyalty', 'set', 'pack', 'box'],
                        help='Sort cards by a specific criterion.')

    # Group: Filtering Options (Standard across tools)
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('--grep', action='append',
                        help='Only include cards matching a search pattern (checks name, typeline, text, cost, and stats). Use multiple times for AND logic.')
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
                        help='Skip cards matching a search pattern (checks name, typeline, text, cost, and stats). Use multiple times for OR logic.')
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
                        help="Only include cards of specific rarities. Supports full names (e.g., 'common', 'mythic') or shorthands: O (Common), N (Uncommon), A (Rare), Y (Mythic), I (Special), L (Basic Land). Supports multiple values (OR logic).")
    filter_group.add_argument('--colors', action='append',
                        help="Only include cards of specific colors (W, U, B, R, G). Use 'C' or 'A' for colorless. Supports multiple values (OR logic).")
    filter_group.add_argument('--identity', action='append',
                        help="Only include cards with specific colors in their color identity (W, U, B, R, G). Use 'C' or 'A' for colorless. Supports multiple values (OR logic).")
    filter_group.add_argument('--id-count', action='append',
                        help='Only include cards with specific color identity counts. Supports inequalities, ranges, and multiple values (OR logic).')
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

    total_matches = len(cards)
    if args.limit > 0:
        cards = cards[:args.limit]
    displayed_matches = len(cards)

    if total_matches == 0 and not args.quiet:
        print("No cards found matching the criteria.", file=sys.stderr)

    # Set default format if none chosen
    if not (args.text or args.table or args.md_table or args.json or args.jsonl or args.csv):
        if args.outfile:
            if args.outfile.endswith('.json'): args.json = True
            elif args.outfile.endswith('.jsonl'): args.jsonl = True
            elif args.outfile.endswith('.csv'): args.csv = True
            elif args.outfile.endswith('.md') or args.outfile.endswith('.mdt'): args.md_table = True
            elif args.outfile.endswith('.tbl') or args.outfile.endswith('.table'): args.table = True
            else: args.text = True
        elif sys.stdout.isatty():
            args.table = True
        else:
            args.text = True

    # Determine if we should use color
    use_color = False
    if args.color is True:
        use_color = True
    elif args.color is None and not (args.json or args.jsonl or args.md_table or args.csv) and sys.stdout.isatty():
        use_color = True

    # Process output
    field_list = [f.strip() for f in args.fields.split(',')]

    # Simulation fields (auto-include)
    sim_fields = []
    if args.box > 0:
        sim_fields = ['box', 'pack']
    elif args.booster > 0:
        sim_fields = ['pack']

    for sf in reversed(sim_fields):
        if sf not in field_list:
            field_list.insert(0, sf)

    # Field Validation
    recognized_fields = set(FIELD_MAP.keys())
    for k, v in FIELD_MAP.items():
        recognized_fields.update(v.get('aliases', []))

    invalid_fields = [f for f in field_list if get_field_canonical_name(f) not in FIELD_MAP]
    if invalid_fields and not args.quiet:
        print(f"Warning: Unrecognized fields: {', '.join(invalid_fields)}", file=sys.stderr)

    # Set up output writer
    output_f = sys.stdout
    if args.outfile:
        if args.verbose:
            print(f"Writing search results to: {args.outfile}", file=sys.stderr)
        output_f = open(args.outfile, 'w', encoding='utf-8')

    try:
        if args.json:
            results = []
            for card in cards:
                card_data = {}
                for field in field_list:
                    card_data[field] = get_field_value(card, field, ansi_color=use_color)
                results.append(card_data)
            output_f.write(json.dumps(results, indent=2) + '\n')
        elif args.jsonl:
            for card in cards:
                card_data = {}
                for field in field_list:
                    card_data[field] = get_field_value(card, field, ansi_color=use_color)
                output_f.write(json.dumps(card_data) + '\n')
        elif args.csv:
            writer = csv.writer(output_f)
            # Header
            header = [FIELD_MAP.get(get_field_canonical_name(f), {}).get('header', f) for f in field_list]
            writer.writerow(header)
            # Content
            for card in cards:
                row = [get_field_value(card, f, ansi_color=use_color) for f in field_list]
                writer.writerow(row)
        elif args.table or args.md_table:
            import datalib
            if total_matches == 0 and not args.md_table:
                # For regular tables with 0 matches, we've already printed a message to stderr
                # and we don't want to print an empty table header.
                pass
            else:
                rows = []
                # Header
                header = []
                for f in field_list:
                    canon = get_field_canonical_name(f)
                    header.append(FIELD_MAP.get(canon, {}).get('header', f.title()))

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
                        canon = get_field_canonical_name(field)
                        align = FIELD_MAP.get(canon, {}).get('align', 'l')
                        if align == 'r':
                            align_row += " ---: |"
                        elif align == 'c':
                            align_row += " :---: |"
                        else:
                            align_row += " :--- |"
                    output_f.write(header_row + '\n')
                    output_f.write(align_row + '\n')
                    for row in rows[1:]:
                        # Escape pipes in markdown
                        escaped_row = [str(cell).replace('|', '\\|').replace('\n', ' ') for cell in row]
                        output_f.write("| " + " | ".join(escaped_row) + " |" + '\n')
                else:
                    # Terminal table output
                    if displayed_matches < total_matches:
                        match_count = f" (Showing {displayed_matches} of {total_matches} matches)"
                    else:
                        match_count = f" ({total_matches} matches)"

                    header_title = "SEARCH RESULTS"
                    header_text = header_title + match_count

                    if use_color:
                        header_main = utils.colorize(header_title, utils.Ansi.BOLD + utils.Ansi.CYAN)
                        header_count = utils.colorize(match_count, utils.Ansi.CYAN)
                        output_f.write("  " + header_main + header_count + '\n')
                    else:
                        output_f.write("  " + header_text + '\n')

                    # Always use a visible separator line for better visual hierarchy
                    output_f.write("  " + "=" * len(header_text) + '\n')

                    aligns = []
                    for field in field_list:
                        canon = get_field_canonical_name(field)
                        aligns.append(FIELD_MAP.get(canon, {}).get('align', 'l'))

                    # Add separator row
                    datalib.add_separator_row(rows)

                    for row in datalib.padrows(rows, aligns=aligns):
                        # Data rows are already indented by 2 spaces in padrows?
                        # No, padrows joins with 2 spaces but doesn't indent the whole line.
                        output_f.write("  " + row + '\n')
        else: # Default text output
            for card in cards:
                card_data = [get_field_value(card, f, ansi_color=use_color) for f in field_list]
                output_f.write(args.delimiter.join(str(val) for val in card_data) + '\n')
    finally:
        if args.outfile:
            output_f.close()

    if not args.quiet:
        utils.print_operation_summary("Search", total_matches, 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
