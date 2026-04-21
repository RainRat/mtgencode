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
from titlecase import titlecase

def main():
    parser = argparse.ArgumentParser(
        description="Profile the 10 primary two-color archetypes in a card dataset. "
                    "Identifies signpost cards, mechanical themes, and curve statistics for each pair.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Two-color archetypes analyzed:
  Allied: WU (Azorius), UB (Dimir), BR (Rakdos), RG (Gruul), GW (Selesnya)
  Enemy: WB (Orzhov), UR (Izzet), BG (Golgari), RW (Boros), GU (Simic)

Usage Examples:
  # Analyze archetypes in a specific set
  python3 scripts/mtg_archetypes.py data/AllPrintings.json --set MOM

  # Compare mechanics of a generated dataset against archetypes
  python3 scripts/mtg_archetypes.py generated_cards.txt
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, XML, or encoded text). Defaults to stdin (-).')

    # Group: Analysis Options
    analysis_group = parser.add_argument_group('Analysis Options')
    analysis_group.add_argument('--min-cards', type=int, default=5,
                                help='Minimum number of cards required to profile an archetype (Default: 5).')
    analysis_group.add_argument('--top-mechanics', type=int, default=3,
                                help='Number of signature mechanics to show per archetype (Default: 3).')

    # Group: Filtering Options (Standard)
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('--grep', action='append', help='Only include cards matching a search pattern.')
    filter_group.add_argument('--vgrep', '--exclude', action='append', dest='vgrep', help='Exclude cards matching a search pattern.')
    filter_group.add_argument('--set', action='append', help='Only include cards from specific sets.')
    filter_group.add_argument('--rarity', action='append', help='Only include cards of specific rarities.')
    filter_group.add_argument('--mechanic', action='append', help='Only include cards with specific mechanical features.')
    filter_group.add_argument('--limit', type=int, default=0, help='Only process the first N cards.')

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
                                  grep=args.grep, vgrep=args.vgrep,
                                  sets=args.set, rarities=args.rarity,
                                  mechanics=args.mechanic)

    if args.limit > 0:
        cards = cards[:args.limit]

    if not cards:
        if not args.quiet:
            print("No cards found matching the criteria.", file=sys.stderr)
        return

    # Define the 10 color pairs (alphabetically sorted to match card.color_identity)
    pairs = ["UW", "BU", "BR", "GR", "GW", "BW", "RU", "BG", "RW", "GU"]

    # Friendly labels for display
    pair_labels = {
        "UW": "WU (Azorius)", "BU": "UB (Dimir)", "BR": "BR (Rakdos)",
        "GR": "RG (Gruul)", "GW": "GW (Selesnya)", "BW": "WB (Orzhov)",
        "RU": "UR (Izzet)", "BG": "BG (Golgari)", "RW": "RW (Boros)", "GU": "GU (Simic)"
    }

    # Archetype buckets: {pair: [cards]}
    archetypes = {p: [] for p in pairs}

    # Global mechanic frequency
    global_mechanics = Counter()
    total_cards = len(cards)

    for card in cards:
        # Calculate global mechanic frequency
        for m in card.mechanics:
            global_mechanics[m] += 1

        # Assign to archetype buckets based on color identity
        identity = card.color_identity
        if len(identity) == 2:
            if identity in archetypes:
                archetypes[identity].append(card)
        elif len(identity) == 1:
            # For monocolored cards, add them to all archetypes that include their color
            for p in pairs:
                if identity in p:
                    archetypes[p].append(card)
        elif not identity:
            # Colorless cards support all archetypes? Usually better to skip them for specific archetype profiling
            # unless they are widely used. For now, we only profile color-affiliated cards.
            pass

    # Filter out empty archetypes or those with too few cards
    active_pairs = [p for p in pairs if len(archetypes[p]) >= max(1, args.min_cards)]

    if not active_pairs:
        if not args.quiet:
            print(f"Insufficient data to profile archetypes (minimum {args.min_cards} cards required per pair).", file=sys.stderr)
        return

    # Profile each archetype
    header = ["Archetype", "Cards", "Signpost Card", "Top Mechanics", "Avg CMC", "Creature %"]
    if use_color:
        header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

    rows = [header]

    for p in active_pairs:
        p_cards = archetypes[p]
        p_count = len(p_cards)

        # 1. Identify Signpost (Multicolored Uncommon)
        signpost = "None"
        uncommons = [c for c in p_cards if c.rarity == utils.rarity_uncommon_marker and len(c.color_identity) == 2]
        if uncommons:
            # Pick the first one as representative
            signpost = titlecase(uncommons[0].name)

        # 2. Calculate Signature Mechanics (Distinctiveness)
        p_mechanics = Counter()
        for c in p_cards:
            for m in c.mechanics:
                p_mechanics[m] += 1

        # Score = (Freq in Pair / Total in Pair) / (Freq Global / Total Global)
        distinctiveness = {}
        for m, count in p_mechanics.items():
            pair_prop = count / p_count
            global_prop = global_mechanics[m] / total_cards
            if global_prop > 0:
                distinctiveness[m] = pair_prop / global_prop

        top_m = sorted(distinctiveness.keys(), key=lambda m: (distinctiveness[m], p_mechanics[m]), reverse=True)[:args.top_mechanics]
        mechanic_str = ", ".join(top_m)

        # 3. Curve Statistics
        avg_cmc = sum(c.cost.cmc for c in p_cards) / p_count
        creature_count = sum(1 for c in p_cards if c.is_creature)
        creature_pct = (creature_count / p_count * 100)

        # Formatting
        label = pair_labels[p]
        if use_color:
            # Colorize the WU/UB/etc part of the label
            code = label.split()[0]
            name = " ".join(label.split()[1:])
            colored_code = "".join([utils.colorize(c, utils.Ansi.get_color_color(c)) for c in code])
            label = f"{colored_code} {name}"

            signpost = utils.colorize(signpost, utils.Ansi.BOLD + utils.Ansi.CYAN) if signpost != "None" else signpost
            mechanic_str = utils.colorize(mechanic_str, utils.Ansi.CYAN)

        rows.append([
            label,
            str(p_count),
            signpost,
            mechanic_str,
            f"{avg_cmc:.2f}",
            f"{creature_pct:5.1f}%"
        ])

    # Display results
    print(utils.colorize("ARCHETYPE PROFILING", utils.Ansi.BOLD + utils.Ansi.CYAN + utils.Ansi.UNDERLINE) if use_color else "=== ARCHETYPE PROFILING ===")
    print(f"Total cards analyzed: {total_cards}\n")

    datalib.add_separator_row(rows)
    datalib.printrows(datalib.padrows(rows, aligns=['l', 'r', 'l', 'l', 'r', 'r']), indent=2)

    if not args.quiet:
        utils.print_operation_summary("Archetype Analysis", total_cards, 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
