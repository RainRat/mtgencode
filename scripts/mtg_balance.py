#!/usr/bin/env python3
import sys
import os
import argparse
from collections import Counter

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import datalib
import cardlib

def get_archetype_counts(cards):
    """Counts cards associated with each of the 10 primary color pairs."""
    # Define the 10 color pairs (alphabetically sorted to match card.color_identity)
    pairs = ["UW", "BU", "BR", "GR", "GW", "BW", "RU", "BG", "RW", "GU"]
    counts = Counter({p: 0 for p in pairs})

    for card in cards:
        identity = card.color_identity
        if len(identity) == 2:
            if identity in counts:
                counts[identity] += 1
        elif len(identity) == 1:
            # Monocolored cards are count-shared across all archetypes containing their color
            for p in pairs:
                if identity in p:
                    counts[p] += 1

    return counts

def main():
    parser = argparse.ArgumentParser(
        description="Analyze and compare the archetype balance (color pair distribution) between datasets.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This tool calculates the 'gravity' of each of the 10 color pairs in a dataset.
It counts multicolored cards directly and monocolored cards as supporting their
respective pairs.

Usage Examples:
  # Compare the balance of a generated set against an official set
  python3 scripts/mtg_balance.py data/AllPrintings.json generated.txt --set MOM

  # See which color pairs are over-represented in a card pool
  python3 scripts/mtg_balance.py my_cards.json
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infiles', nargs='+',
                        help='Input card data files (JSON, CSV, encoded text, etc.). First file is used as the baseline.')

    # Group: Filtering Options
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('--set', action='append', help='Only include cards from specific sets.')
    filter_group.add_argument('--rarity', action='append', help='Only include cards of specific rarities.')
    filter_group.add_argument('--limit', type=int, default=0, help='Only process the first N cards from each input.')

    # Group: Logging & Debugging
    debug_group = parser.add_argument_group('Logging & Debugging')
    debug_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    debug_group.add_argument('-q', '--quiet', action='store_true', help='Suppress status messages.')

    color_group = debug_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color output.')

    args = parser.parse_args()

    use_color = False
    if args.color is True:
        use_color = True
    elif args.color is None and sys.stdout.isatty():
        use_color = True

    # Load datasets
    datasets = []
    for f in args.infiles:
        cards = jdecode.mtg_open_file(f, verbose=args.verbose, sets=args.set, rarities=args.rarity)
        if args.limit > 0:
            cards = cards[:args.limit]
        if not cards:
            if not args.quiet:
                print(f"Warning: No cards found in {f} matching criteria.", file=sys.stderr)
            continue
        datasets.append({
            'name': os.path.basename(f)[:15],
            'counts': get_archetype_counts(cards),
            'total': len(cards)
        })

    if not datasets:
        return

    # Table Setup
    pairs = ["UW", "BU", "BR", "GR", "GW", "BW", "RU", "BG", "RW", "GU"]
    pair_labels = {
        "UW": "WU (Azorius)", "BU": "UB (Dimir)", "BR": "BR (Rakdos)",
        "GR": "RG (Gruul)", "GW": "GW (Selesnya)", "BW": "WB (Orzhov)",
        "RU": "UR (Izzet)", "BG": "BG (Golgari)", "RW": "RW (Boros)", "GU": "GU (Simic)"
    }

    base = datasets[0]
    header = ["Archetype", f"% {base['name']}"]
    for i in range(1, len(datasets)):
        header.extend([f"% {datasets[i]['name']}", "Delta"])

    if use_color:
        header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

    rows = [header]

    for p in pairs:
        label = pair_labels[p]
        if use_color:
            parts = label.split(None, 1)
            code = parts[0]
            name = parts[1] if len(parts) > 1 else ""
            colored_code = "".join([utils.colorize(c, utils.Ansi.get_color_color(c)) for c in code])
            label = f"{colored_code} {name}"

        base_pct = (base['counts'][p] / base['total'] * 100) if base['total'] > 0 else 0
        row = [label, f"{base_pct:5.1f}%"]

        for i in range(1, len(datasets)):
            ds = datasets[i]
            pct = (ds['counts'][p] / ds['total'] * 100) if ds['total'] > 0 else 0
            delta = pct - base_pct

            delta_str = f"{delta:+5.1f}%"
            if use_color:
                if delta > 2.0:
                    delta_str = utils.colorize(delta_str, utils.Ansi.BOLD + utils.Ansi.GREEN)
                elif delta < -2.0:
                    delta_str = utils.colorize(delta_str, utils.Ansi.BOLD + utils.Ansi.RED)

            row.extend([f"{pct:5.1f}%", delta_str])

        rows.append(row)

    # Print Report
    utils.print_header("ARCHETYPE BALANCE COMPARISON", use_color=use_color)
    print(f"  Baseline: {base['name']} ({base['total']} cards)\n")

    datalib.add_separator_row(rows)
    datalib.printrows(datalib.padrows(rows, aligns=['l'] + ['r'] * (len(header)-1)), indent=2)

    if not args.quiet:
        utils.print_operation_summary("Balance Analysis", sum(ds['total'] for ds in datasets), 0)

if __name__ == "__main__":
    main()
