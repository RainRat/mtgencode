#!/usr/bin/env python3
import sys
import os
import argparse
import csv
import json

# Ensure lib is in path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)
import jdecode
import utils

RARITY_MAPPING = {"R": "rare", "U": "uncommon", "C": "common", "M": "mythic", "L": "basic land", "I": "special"}

def process_face(name, cost, type_line, subtypes, text, stats, rarity):
    temprarity = RARITY_MAPPING.get(rarity, rarity)
    face = {
        "name": name,
        "manaCost": cost,
        "rarity": temprarity,
        "text": text.replace("\\n", "\n"),
    }

    # supertypes, types, subtypes
    supertypes, types = utils.split_types(type_line)
    if supertypes:
        face["supertypes"] = supertypes
    face["types"] = types
    if subtypes != "":
        face["subtypes"] = subtypes.split(" ")

    if stats != "":
        pt = stats.split("/")
        if len(pt) >= 2:
            face["power"] = pt[0]
            face["toughness"] = pt[1]
        else:
            if "Planeswalker" in types:
                face["loyalty"] = stats
            elif "Battle" in types:
                face["defense"] = stats
            else:
                face["pt"] = stats

    # create "type" (full type line)
    fulltypes = type_line
    if subtypes != "":
        fulltypes = fulltypes + " — " + subtypes
    face["type"] = fulltypes

    return face

def run_csv2json(argv=None):
    parser = argparse.ArgumentParser(
        description='Convert a CSV file of custom Magic cards into MTGJSON format.',
        epilog='''
Custom Card Workflow:
  1. Create a CSV file (e.g., custom.csv) following the format below.
  2. Convert to JSON:
     python3 scripts/mtg_csv_json.py csv2json custom.csv custom.json
  3. Merge with official data:
     python3 scripts/combinejson.py data/AllPrintings.json custom.json AllCustom.json

CSV Format (7 columns in this order):
  1. Name: The name of the card (e.g., "Giant Growth").
  2. Mana Cost: The mana symbols in braces (e.g., "{G}" or "{1}{W}{B}").
  3. Types: Supertypes and card types (e.g., "Legendary Creature").
  4. Subtypes: Subtypes separated by spaces (e.g., "Elf Warrior").
  5. Text: Rules text. Use "\\n" or literal newlines for new lines.
  6. Stats: Power/Toughness (3/3), Loyalty (5), or Defense (3).
  7. Rarity: Short marker (C, U, R, M, L, I) or full name (common, rare, etc.).

Multi-Faced Cards:
  To represent cards with multiple faces (e.g., Splits or Transforms), use the
  " // " separator in the relevant columns.
  Example: Name: "Front // Back", Cost: "{1}{W} // {U}", Type: "Creature // Instant"

Note: The first row is ignored if the first column is exactly "name".
''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('csv_file', help='Path to the input CSV file.')
    parser.add_argument('json_output', help='Path to the output JSON file.')
    args = parser.parse_args(argv)

    with open(args.csv_file, encoding='utf-8') as csvfile, open(args.json_output, 'w', encoding='utf-8') as jsonfile:
        reader = csv.reader(csvfile)
        json_data = {"data": {"CUS": {"type": "custom", "cards": [], "name": "custom", "code": "CUS"}}}

        for row in reader:
            if not row or row[0] == "name":
                continue

            # Check for multi-faced cards via ' // ' in any column
            is_multi = any(' // ' in str(row[i]) for i in range(len(row)))

            if is_multi:
                # Split fields
                front_args = []
                back_args = []
                for i in range(min(7, len(row))):
                    val = row[i]
                    if ' // ' in val:
                        parts = val.split(' // ', 1)
                        front_args.append(parts[0])
                        back_args.append(parts[1])
                    else:
                        front_args.append(val)
                        back_args.append(val)

                # Pad if row has fewer than 7 columns (though format specifies 7)
                while len(front_args) < 7:
                    front_args.append("")
                    back_args.append("")

                card = process_face(*front_args)
                bside = process_face(*back_args)
                card["bside"] = bside
                card["layout"] = "transform" # Standard multi-face layout
            else:
                args_list = row[:7]
                while len(args_list) < 7:
                    args_list.append("")
                card = process_face(*args_list)
                card["layout"] = "normal"

            card["setCode"] = "CUS"
            json_data["data"]["CUS"]["cards"].append(card)

        json.dump(json_data, jsonfile)

def run_json2csv(argv=None):
    parser = argparse.ArgumentParser(
        description="Converts MTG card data into the CSV format used by csv2json.py and the custom card template.",
        epilog='''
Multi-Faced Cards:
  This script supports multi-faced cards (Splits, Transforms, Battles). All faces
  are exported into a single CSV row, with fields merged using the " // " separator.
  This format is compatible with csv2json.py for round-trip data processing.
''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', help='Input card data (JSON, JSONL, MSE, ZIP, or encoded text).')
    io_group.add_argument('outfile', help='Output CSV file path.')

    # Group: Filtering Options
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
                        help='Exclude cards matching a search pattern (checks name, type, and text). Use multiple times for OR logic.')
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
                        help='Only include cards from specific sets (e.g., MOM, MRD). Supports multiple sets (OR logic).')
    filter_group.add_argument('--rarity', action='append',
                        help="Only include cards of specific rarities. Supports full names or shorthands (O, N, A, Y, I, L). Supports multiple rarities.")
    filter_group.add_argument('--colors', action='append',
                        help="Only include cards of specific colors (W, U, B, R, G, C/A). Supports multiple colors.")
    filter_group.add_argument('--cmc', action='append',
                        help='Only include cards with specific CMC values. Supports inequalities and ranges.')
    filter_group.add_argument('--pow', '--power', action='append', dest='pow',
                        help='Only include cards with specific Power values. Supports inequalities and ranges.')
    filter_group.add_argument('--tou', '--toughness', action='append', dest='tou',
                        help='Only include cards with specific Toughness values. Supports inequalities and ranges.')
    filter_group.add_argument('--loy', '--loyalty', '--defense', action='append', dest='loy',
                        help='Only include cards with specific Loyalty or Defense values. Supports inequalities and ranges.')
    filter_group.add_argument('--mechanic', action='append',
                        help='Only include cards with specific mechanical features or keyword abilities. Supports multiple values.')
    filter_group.add_argument('--deck-filter', '--decklist-filter', dest='deck',
                        help='Filter cards using a standard MTG decklist file.')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')

    args = parser.parse_args(argv)

    # Load cards using the standard loader
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
                                  decklist_file=args.deck)

    if not cards:
        if args.verbose:
            print("No cards found matching the criteria.", file=sys.stderr)
        return

    with open(args.outfile, 'w', encoding='utf8', newline='') as f:
        writer = csv.writer(f)
        # Header row compatible with csv2json.py
        writer.writerow(['name', 'mana_cost', 'type', 'subtypes', 'text', 'pt', 'rarity'])

        for card in cards:
            row = card._get_csv_data()
            writer.writerow(row)

    if args.verbose:
        print(f"Successfully exported {len(cards)} cards to {args.outfile}")

    utils.print_operation_summary("CSV Export", len(cards), 0, quiet=not args.verbose)

def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "csv2json":
            run_csv2json(sys.argv[2:])
            return
        elif cmd == "json2csv":
            run_json2csv(sys.argv[2:])
            return

    # Auto-detection mode or direct parser
    # If first argument isn't an explicit command, check file extensions or help
    parser = argparse.ArgumentParser(
        description="Consolidated CSV and JSON utility for Magic: The Gathering card datasets.",
        epilog="""
Usage:
  python3 scripts/mtg_csv_json.py csv2json <csv_file> <json_output>
  python3 scripts/mtg_csv_json.py json2csv <infile> <outfile> [filters...]

Autodetect mode:
  You can also invoke it without subcommands, and the utility will determine the direction based on file extensions:
  python3 scripts/mtg_csv_json.py <infile> <outfile> [filters...]
""",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    # We define dummy positionals to capture the autodetect args
    parser.add_argument('infile', nargs='?', help='Input file (.csv or .json)')
    parser.add_argument('outfile', nargs='?', help='Output file (.json or .csv)')
    
    # We parse known args to check if we can autodetect, otherwise show help
    args, remaining = parser.parse_known_args()
    
    if not args.infile or not args.outfile:
        parser.print_help()
        sys.exit(0)

    # Detect conversion direction
    in_ext = os.path.splitext(args.infile)[1].lower()
    out_ext = os.path.splitext(args.outfile)[1].lower()

    if in_ext == '.csv' or out_ext == '.json':
        # CSV to JSON
        # For CSV to JSON, we don't expect filters
        run_csv2json(sys.argv[1:])
    else:
        # JSON to CSV
        run_json2csv(sys.argv[1:])

if __name__ == "__main__":
    main()
