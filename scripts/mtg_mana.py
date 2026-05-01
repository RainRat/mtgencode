#!/usr/bin/env python3
import sys
import os
import argparse
import json
import csv
import re
from collections import defaultdict, Counter

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import datalib
import cardlib

def get_produced_colors(card):
    """
    Identifies colors produced by a card based on rules text and land types.
    Returns a set of color characters (W, U, B, R, G, C) or 'Any'.
    """
    produced = set()

    # 1. Intrinsic basic land production (even if text is empty)
    # Check both types and subtypes for basic land types
    all_types = [t.lower() for t in card.types + card.subtypes]
    if 'plains' in all_types: produced.add('W')
    if 'island' in all_types: produced.add('U')
    if 'swamp' in all_types: produced.add('B')
    if 'mountain' in all_types: produced.add('R')
    if 'forest' in all_types: produced.add('G')

    # 2. Check for rules text patterns
    text = card.get_text(force_unpass=True).lower()

    # "Any Color" patterns
    any_patterns = [
        "any color",
        "any chosen color",
        "one mana of any color",
        "any combination of colors"
    ]
    if any(p in text for p in any_patterns):
        produced = {"Any"}
    else:
        # Check for "Add" followed by symbols
        for match in re.finditer(r'[Aa]dd\s+([^.]+)', text):
            sentence_part = match.group(1)
            # Find symbols like {G}, {W/U}, {C}
            symbols = re.findall(r'\{([^}]+)\}', sentence_part)
            for sym in symbols:
                for char in sym.upper():
                    if char in 'WUBRGC':
                        produced.add(char)

        # Also check for "Add one [color] mana" (common in older text or simplified formats)
        color_map = {
            'white': 'W', 'blue': 'U', 'black': 'B', 'red': 'R', 'green': 'G', 'colorless': 'C'
        }
        for color_name, char in color_map.items():
            if re.search(r'[Aa]dd\s+(?:one|two|three|X)\s+' + color_name, text):
                produced.add(char)

    # Recursive check for b-sides (e.g. flip/transform mana producers)
    if card.bside:
        b_produced = get_produced_colors(card.bside)
        if "Any" in b_produced:
            return {"Any"}
        produced.update(b_produced)

    return produced

def get_category(card):
    """Categorizes a mana producer."""
    if card.is_creature: return "Dork"
    if card.is_artifact: return "Rock"
    if card.is_land: return "Land"
    if card.is_instant or card.is_sorcery: return "Ritual"
    return "Other"

def analyze_dataset(cards):
    """Analyzes mana production for a list of cards."""
    producers = []
    stats = {
        'total_cards': len(cards),
        'producer_count': 0,
        'categories': Counter(),
        'colors': Counter(),
        'fixing_count': 0, # Produces 2+ colors or Any
    }

    for card in cards:
        produced = get_produced_colors(card)
        if produced:
            stats['producer_count'] += 1
            producers.append((card, produced))

            cat = get_category(card)
            stats['categories'][cat] += 1

            if "Any" in produced:
                stats['colors']['Any'] += 1
                stats['fixing_count'] += 1
            else:
                for c in produced:
                    stats['colors'][c] += 1
                if len(produced) >= 2:
                    stats['fixing_count'] += 1

    return stats, producers

def main():
    parser = argparse.ArgumentParser(
        description="Identify and profile mana-producing cards in a dataset.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool identifies mana producers using rules text patterns (e.g., 'Add {G}', 'any color') and intrinsic basic land types. It categorizes producers into Dorks (creatures), Rocks (artifacts), Lands, and Rituals (spells).

Usage Examples:
  # Analyze mana production for a specific set
  python3 scripts/mtg_mana.py data/AllPrintings.json --set MOM

  # Compare mana fixing between official data and AI-generated cards
  python3 scripts/mtg_mana.py data/AllPrintings.json --compare generated.txt

  # Find only green mana-producing creatures (Mana Dorks)
  python3 scripts/mtg_mana.py data/AllPrintings.json --colors G --grep-type "Creature"
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, XML, or encoded text). Defaults to stdin (-) or data/AllPrintings.json if available.')
    io_group.add_argument('--compare', '-c',
                        help='Optional second dataset to compare against the primary input.')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Path to save results. If not provided, results print to the console.')

    # Group: Output Format
    fmt_group_title = parser.add_argument_group('Output Format')
    fmt_group = fmt_group_title.add_mutually_exclusive_group()
    fmt_group.add_argument('--table', action='store_true', help='Generate a formatted table (Default for terminal).')
    fmt_group.add_argument('--json', action='store_true', help='Generate a JSON file (Auto-detected for .json).')
    fmt_group.add_argument('--csv', action='store_true', help='Generate a CSV file (Auto-detected for .csv).')

    # Group: Filtering Options (Standard)
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('--grep', action='append', help='Only include cards matching a search pattern.')
    filter_group.add_argument('--vgrep', '--exclude', action='append', dest='vgrep', help='Exclude cards matching a search pattern.')
    filter_group.add_argument('--set', action='append', help='Only include cards from specific sets.')
    filter_group.add_argument('--rarity', action='append', help='Only include cards of specific rarities.')
    filter_group.add_argument('--colors', action='append', help='Only include cards of specific colors.')
    filter_group.add_argument('--identity', action='append', help='Only include cards with specific color identities.')
    filter_group.add_argument('--cmc', action='append', help='Only include cards with specific CMC values.')
    filter_group.add_argument('--mechanic', action='append', help='Only include cards with specific mechanical features.')
    filter_group.add_argument('--limit', type=int, default=0, help='Only process the first N cards.')
    filter_group.add_argument('--shuffle', action='store_true', help='Randomize card order.')
    filter_group.add_argument('--sample', type=int, default=0, help='Pick N random cards.')
    filter_group.add_argument('--seed', type=int, help='Seed for random generator.')
    filter_group.add_argument('--booster', type=int, default=0, help='Simulate opening N booster packs.')
    filter_group.add_argument('--box', type=int, default=0, help='Simulate opening N booster boxes.')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    debug_group.add_argument('-q', '--quiet', action='store_true', help='Suppress status messages.')

    # Color options
    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color output.')

    args = parser.parse_args()

    # UX Improvement: Default Dataset
    # If we are reading from stdin but it's an interactive terminal, use AllPrintings.json if it exists.
    if (args.infile == '-' or args.infile is None) and sys.stdin.isatty():
        script_dir = os.path.dirname(os.path.realpath(__file__))
        default_data = os.path.join(script_dir, '../data/AllPrintings.json')
        if os.path.exists(default_data):
            args.infile = default_data
            if not getattr(args, 'quiet', False):
                print(f"Notice: Using default dataset: {args.infile}", file=sys.stderr)
        elif os.path.exists('data/AllPrintings.json'):
            args.infile = 'data/AllPrintings.json'
            if not getattr(args, 'quiet', False):
                print(f"Notice: Using default dataset: {args.infile}", file=sys.stderr)

    if args.sample > 0:
        args.shuffle = True
        args.limit = args.sample

    # Format detection
    if not (args.json or args.csv or args.table):
        if args.outfile:
            if args.outfile.endswith('.json'): args.json = True
            elif args.outfile.endswith('.csv'): args.csv = True
            else: args.table = True
        else:
            args.table = True

    # Color detection
    use_color = False
    if args.color is True:
        use_color = True
    elif args.color is None and not (args.json or args.csv) and sys.stdout.isatty():
        use_color = True

    # Load primary cards
    cards1 = jdecode.mtg_open_file(args.infile, verbose=args.verbose,
                                   grep=args.grep, vgrep=args.vgrep,
                                   sets=args.set, rarities=args.rarity,
                                   colors=args.colors, cmcs=args.cmc,
                                   mechanics=args.mechanic,
                                   identities=args.identity,
                                   shuffle=args.shuffle, seed=args.seed,
                                   booster=args.booster, box=args.box)
    if args.limit > 0:
        cards1 = cards1[:args.limit]

    if not cards1:
        if not args.quiet:
            print(f"No cards found in {args.infile} matching the criteria.", file=sys.stderr)
        return

    stats1, producers1 = analyze_dataset(cards1)

    # Load comparison cards if provided
    stats2, producers2 = None, None
    if args.compare:
        cards2 = jdecode.mtg_open_file(args.compare, verbose=args.verbose,
                                       grep=args.grep, vgrep=args.vgrep,
                                       sets=args.set, rarities=args.rarity,
                                       colors=args.colors, cmcs=args.cmc,
                                       mechanics=args.mechanic,
                                       identities=args.identity,
                                       shuffle=args.shuffle, seed=args.seed,
                                       booster=args.booster, box=args.box)
        if args.limit > 0:
            cards2 = cards2[:args.limit]
        if cards2:
            stats2, producers2 = analyze_dataset(cards2)

    # Output
    output_f = sys.stdout
    if args.outfile:
        output_f = open(args.outfile, 'w', encoding='utf-8')

    try:
        if args.json:
            result = {'primary': stats1}
            if stats2: result['comparison'] = stats2
            output_f.write(json.dumps(result, indent=2) + '\n')
        elif args.csv:
            writer = csv.writer(output_f)
            writer.writerow(['Dataset', 'Category', 'Metric', 'Value'])
            for s, label in [(stats1, 'Primary'), (stats2, 'Comparison')]:
                if not s: continue
                for cat, count in s['categories'].items():
                    writer.writerow([label, 'Category Breakdown', cat, count])
                for color, count in s['colors'].items():
                    writer.writerow([label, 'Color Production', color, count])
                writer.writerow([label, 'General', 'Fixing Density', f"{s['fixing_count']/s['total_cards']*100:.2f}%"])
                writer.writerow([label, 'General', 'Producer Count', s['producer_count']])
                writer.writerow([label, 'General', 'Total Cards', s['total_cards']])
        else:
            # Table Output
            title = "MANA PRODUCTION ANALYSIS"
            if stats2:
                title += " (COMPARISON)"
            utils.print_header(title, count=stats1['total_cards'], use_color=use_color, file=output_f)

            # 1. Summary Metrics
            print(f"  {datalib.color_line('General Metrics:', use_color)}", file=output_f)
            fname1 = os.path.basename(args.infile)[:15]
            header = ["Metric", fname1]
            if stats2:
                fname2 = os.path.basename(args.compare)[:15]
                header.append(fname2)
                header.append("Delta")

            if use_color:
                header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

            rows = [header]
            metrics = [
                ("Total Producers", stats1['producer_count'], stats2['producer_count'] if stats2 else None),
                ("Fixing Cards", stats1['fixing_count'], stats2['fixing_count'] if stats2 else None),
                ("Fixing Density", f"{stats1['fixing_count']/stats1['total_cards']*100:5.1f}%",
                                   f"{stats2['fixing_count']/stats2['total_cards']*100:5.1f}%" if stats2 else None)
            ]

            for label, val1, val2 in metrics:
                row = [label, val1]
                if stats2:
                    row.append(val2)
                    # Simple delta for numeric
                    try:
                        v1 = float(str(val1).replace('%',''))
                        v2 = float(str(val2).replace('%',''))
                        delta = v2 - v1
                        delta_str = f"{delta:+.1f}" + ("%" if "%" in str(val1) else "")
                        if use_color:
                            if delta > 0.5: delta_str = utils.colorize(delta_str, utils.Ansi.GREEN)
                            elif delta < -0.5: delta_str = utils.colorize(delta_str, utils.Ansi.RED)
                        row.append(delta_str)
                    except:
                        row.append("-")
                rows.append(row)

            datalib.add_separator_row(rows)
            datalib.printrows(datalib.padrows(rows), indent=4)
            print("", file=output_f)

            # 2. Category Breakdown
            print(f"  {datalib.color_line('Producer Categories:', use_color)}", file=output_f)
            c_header = ["Category", f"% {fname1}"]
            if stats2:
                c_header.append(f"% {fname2}")
                c_header.append("Delta")
            else:
                c_header.append("Percent")
                c_header.append("Distribution")

            if use_color:
                c_header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in c_header]

            c_rows = [c_header]
            for cat in ["Dork", "Rock", "Land", "Ritual", "Other"]:
                p1 = stats1['categories'][cat] / stats1['total_cards'] * 100
                row = [cat, f"{p1:5.1f}%"]
                if stats2:
                    p2 = stats2['categories'][cat] / stats2['total_cards'] * 100
                    delta = p2 - p1
                    delta_str = f"{delta:+.1f}%"
                    if use_color:
                        if delta > 1.0: delta_str = utils.colorize(delta_str, utils.Ansi.GREEN)
                        elif delta < -1.0: delta_str = utils.colorize(delta_str, utils.Ansi.RED)
                    row.extend([f"{p2:5.1f}%", delta_str])
                else:
                    count = stats1['categories'][cat]
                    bar = datalib.get_bar_chart(p1, use_color, color=utils.Ansi.CYAN)
                    row = [cat, count, f"{p1:5.1f}%", bar]
                c_rows.append(row)

            datalib.add_separator_row(c_rows)
            datalib.printrows(datalib.padrows(c_rows), indent=4)
            print("", file=output_f)

            # 3. Produced Colors
            print(f"  {datalib.color_line('Produced Colors:', use_color)}", file=output_f)
            col_header = ["Color", f"% {fname1}"]
            if stats2:
                col_header.append(f"% {fname2}")
                col_header.append("Delta")
            else:
                col_header.append("Count")
                col_header.append("Percent")
                col_header.append("Frequency")

            if use_color:
                col_header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in col_header]

            col_rows = [col_header]
            for c in list("WUBRGC") + ["Any"]:
                p1 = stats1['colors'][c] / stats1['total_cards'] * 100
                if p1 == 0 and c != "Any" and not (stats2 and stats2['colors'][c] > 0): continue

                display_c = c
                if use_color:
                    display_c = utils.colorize(c, utils.Ansi.get_color_color(c)) if c != "Any" else utils.colorize(c, utils.Ansi.YELLOW)

                row = [display_c, f"{p1:5.1f}%"]
                if stats2:
                    p2 = stats2['colors'][c] / stats2['total_cards'] * 100
                    delta = p2 - p1
                    delta_str = f"{delta:+.1f}%"
                    if use_color:
                        if delta > 1.0: delta_str = utils.colorize(delta_str, utils.Ansi.GREEN)
                        elif delta < -1.0: delta_str = utils.colorize(delta_str, utils.Ansi.RED)
                    row.extend([f"{p2:5.1f}%", delta_str])
                else:
                    count = stats1['colors'][c]
                    bar = datalib.get_bar_chart(p1, use_color, color=utils.Ansi.get_color_color(c) if c != "Any" else utils.Ansi.YELLOW)
                    row = [display_c, count, f"{p1:5.1f}%", bar]
                col_rows.append(row)

            datalib.add_separator_row(col_rows)
            datalib.printrows(datalib.padrows(col_rows), indent=4)
            print("", file=output_f)

    finally:
        if args.outfile:
            output_f.close()

    if not args.quiet:
        utils.print_operation_summary("Mana Analysis", stats1['total_cards'], 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
