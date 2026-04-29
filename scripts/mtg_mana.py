#!/usr/bin/env python3
import sys
import os
import argparse
from collections import Counter, defaultdict

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import datalib
import cardlib

def analyze_mana_production(card):
    """
    Analyzes a card to determine if it produces mana and which colors.
    Returns (is_producer, colors, is_fixing, is_any_color)
    """
    is_producer = False
    produced_colors = set()
    is_any_color = False

    # Primary check: Rules text lines
    for line in card.text_lines:
        lt = line.text.lower()
        # Look for "add " which is the standard verb for mana production
        if "add " in lt:
            # Check for "any color"
            if "any color" in lt or "mana of any type" in lt:
                is_producer = True
                is_any_color = True
                produced_colors.update(['W', 'U', 'B', 'R', 'G'])

            # Check for specific mana symbols in this line
            if line.costs:
                # We assume if "add " is in the line, the symbols are what's being added
                # This holds for 99% of cards.
                for cost in line.costs:
                    has_actual_mana = False
                    for c in cost.colors:
                        produced_colors.add(c)
                        has_actual_mana = True
                    if cost.colorless > 0 or cost.allsymbols.get('C', 0) > 0:
                        produced_colors.add('C')
                        has_actual_mana = True

                    if has_actual_mana:
                        is_producer = True

            # Fallback for "add {mana}" where mana is a word (rare in modern templating)
            if "mana" in lt and not is_producer:
                is_producer = True

    # Special handling for basic land types which have intrinsic mana production
    # (MTGJSON usually includes the oracle text for these now, but good to be safe)
    # We use lowercase keys because cardlib lowercases subtypes during parsing.
    intrinsic_map = {
        'plains': 'W', 'island': 'U', 'swamp': 'B', 'mountain': 'R', 'forest': 'G'
    }
    for st in card.subtypes:
        if st.lower() in intrinsic_map:
            is_producer = True
            produced_colors.add(intrinsic_map[st.lower()])

    # Fixing is defined as producing more than one color or any color
    is_fixing = is_any_color or len([c for c in produced_colors if c != 'C']) > 1

    return is_producer, produced_colors, is_fixing, is_any_color

def get_producer_category(card):
    """Categorizes the type of mana producer."""
    if card.is_creature:
        return "Mana Dork"
    elif card.is_artifact:
        return "Mana Rock"
    elif card.is_land:
        return "Land"
    elif card.is_instant or card.is_sorcery:
        return "Ritual"
    elif card.is_enchantment:
        return "Enchantment"
    else:
        return "Other"

def main():
    parser = argparse.ArgumentParser(
        description="Analyze the mana production and color fixing infrastructure of a card dataset.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool identifies cards that generate mana and provides a breakdown of how
mana is produced across the dataset. It categorizes producers into Dorks, Rocks,
Lands, and Rituals, and analyzes color distribution.

Usage Examples:
  # Analyze mana production for a specific set
  python3 scripts/mtg_mana.py data/AllPrintings.json --set MOM

  # Compare mana production between two sets
  python3 scripts/mtg_mana.py data/SetA.json --compare data/SetB.json

  # Analyze only rare and mythic producers
  python3 scripts/mtg_mana.py data/AllPrintings.json --rarity rare --rarity mythic
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, XML, or encoded text). Defaults to stdin (-).')
    io_group.add_argument('--compare', '-c',
                        help='Optional second dataset to compare against the primary input.')

    # Group: Content Formatting
    proc_group = parser.add_argument_group('Data Processing')
    proc_group.add_argument('-n', '--limit', type=int, default=0, help='Only process the first N cards.')
    proc_group.add_argument('--shuffle', action='store_true', help='Randomize cards before analysis.')

    # Group: Filtering Options
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('--grep', action='append', help='Only include cards matching a pattern.')
    filter_group.add_argument('--set', action='append', help='Only include specific sets.')
    filter_group.add_argument('--rarity', action='append', help='Only include specific rarities.')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed messages.')
    debug_group.add_argument('-q', '--quiet', action='store_true', help='Suppress status messages.')

    # Color options
    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color output.')

    args = parser.parse_args()

    # Determine color usage
    use_color = False
    if args.color is True:
        use_color = True
    elif args.color is None and sys.stdout.isatty():
        use_color = True

    def load_and_analyze(path):
        if not path:
            return None

        cards = jdecode.mtg_open_file(path, verbose=args.verbose,
                                      grep=args.grep, sets=args.set, rarities=args.rarity,
                                      shuffle=args.shuffle)
        if args.limit > 0:
            cards = cards[:args.limit]

        if not cards:
            return None

        stats = {
            'total_cards': len(cards),
            'producers': [],
            'categories': Counter(),
            'colors': Counter(),
            'fixing_count': 0,
            'any_color_count': 0
        }

        for card in cards:
            is_prod, colors, is_fixing, is_any = analyze_mana_production(card)
            if is_prod:
                stats['producers'].append(card)
                stats['categories'][get_producer_category(card)] += 1
                for c in colors:
                    stats['colors'][c] += 1
                if is_any:
                    stats['any_color_count'] += 1
                if is_fixing:
                    stats['fixing_count'] += 1

        return stats

    stats1 = load_and_analyze(args.infile)
    if not stats1:
        print(f"No cards found in {args.infile} matching criteria.", file=sys.stderr)
        return

    stats2 = load_and_analyze(args.compare)

    # 1. Header
    title = "MANA PRODUCTION ANALYSIS"
    utils.print_header(title, use_color=use_color)

    def print_stats(stats, label=None):
        if label:
            print(f"\n  {utils.colorize(label, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) if use_color else '=== ' + label + ' ==='}")

        total = stats['total_cards']
        prod_count = len(stats['producers'])
        prod_pct = (prod_count / total * 100) if total > 0 else 0

        print(f"    Total Cards:  {total}")
        print(f"    Mana Producers: {datalib.color_count(prod_count, use_color)} ({prod_pct:.1f}%)")

        # Category Breakdown
        print(f"\n    {datalib.color_line('Producer Categories:', use_color)}")
        cat_rows = [["Category", "Count", "Percent", "Chart"]]
        if use_color:
            cat_rows[0] = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in cat_rows[0]]

        for cat in ["Land", "Mana Rock", "Mana Dork", "Ritual", "Enchantment", "Other"]:
            count = stats['categories'][cat]
            if count == 0: continue
            pct = (count / total * 100)
            bar = datalib.get_bar_chart(pct * (total/prod_count) if prod_count > 0 else 0, use_color, color=utils.Ansi.CYAN)
            cat_rows.append([cat, str(count), f"{pct:.1f}%", bar])

        datalib.printrows(datalib.padrows(cat_rows, aligns=['l', 'r', 'r', 'l']), indent=6)

        # Color Breakdown
        print(f"\n    {datalib.color_line('Produced Colors:', use_color)}")
        color_rows = [["Color", "Count", "Percent", "Chart"]]
        if use_color:
            color_rows[0] = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in color_rows[0]]

        for c in "WUBRGC":
            count = stats['colors'][c]
            if count == 0: continue
            pct = (count / total * 100)
            # Use color-specific bar if possible
            bar_color = utils.Ansi.get_color_color(c) if use_color else None
            bar = datalib.get_bar_chart(pct * (total/prod_count) if prod_count > 0 else 0, use_color, color=bar_color)
            color_rows.append([c, str(count), f"{pct:.1f}%", bar])

        datalib.printrows(datalib.padrows(color_rows, aligns=['c', 'r', 'r', 'l']), indent=6)

        # Fixing Stats
        fix_pct = (stats['fixing_count'] / total * 100) if total > 0 else 0
        print(f"\n    Color Fixing: {datalib.color_count(stats['fixing_count'], use_color)} cards ({fix_pct:.1f}% of dataset)")
        if stats['any_color_count'] > 0:
            print(f"    Any Color:    {stats['any_color_count']} cards")

    if stats2:
        print_stats(stats1, label=os.path.basename(args.infile))
        print_stats(stats2, label=os.path.basename(args.compare))

        # Delta summary
        print(f"\n  {utils.colorize('COMPARISON SUMMARY:', utils.Ansi.BOLD + utils.Ansi.YELLOW) if use_color else '--- COMPARISON SUMMARY ---'}")
        p1 = (len(stats1['producers']) / stats1['total_cards'] * 100)
        p2 = (len(stats2['producers']) / stats2['total_cards'] * 100)
        delta = p2 - p1
        delta_str = f"{delta:+.1f}%"
        if use_color:
            if delta > 2: delta_str = utils.colorize(delta_str, utils.Ansi.BOLD + utils.Ansi.GREEN)
            elif delta < -2: delta_str = utils.colorize(delta_str, utils.Ansi.BOLD + utils.Ansi.RED)

        print(f"    Mana Density Delta: {delta_str}")

        f1 = (stats1['fixing_count'] / stats1['total_cards'] * 100)
        f2 = (stats2['fixing_count'] / stats2['total_cards'] * 100)
        f_delta = f2 - f1
        f_delta_str = f"{f_delta:+.1f}%"
        if use_color:
            if f_delta > 1: f_delta_str = utils.colorize(f_delta_str, utils.Ansi.BOLD + utils.Ansi.GREEN)
            elif f_delta < -1: f_delta_str = utils.colorize(f_delta_str, utils.Ansi.BOLD + utils.Ansi.RED)
        print(f"    Fixing Density Delta: {f_delta_str}")

    else:
        print_stats(stats1)

    if not args.quiet:
        utils.print_operation_summary("Mana Analysis", stats1['total_cards'], 0)

if __name__ == "__main__":
    main()
