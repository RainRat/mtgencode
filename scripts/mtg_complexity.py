#!/usr/bin/env python3
import sys
import os
import argparse
import json
import re
from collections import defaultdict

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import datalib
import cardlib
from titlecase import titlecase

def calculate_complexity_score(card):
    """
    Calculates a heuristic 'Complexity Score' for a card.
    Inspired by MTG Design's 'New World Order' (NWO) guidelines.
    """
    score = 0

    # 1. Text Length: 1 point per 15 characters of rules text (unpassed)
    text = card.get_text(force_unpass=True)
    score += len(text) / 15.0

    # 2. Structural Complexity: 2 points per line of text
    lines = [l for l in text.split('\n') if l.strip()]
    score += len(lines) * 2.0

    # 3. Mechanical Breadth: 3 points per recognized mechanic
    # We use get_face_mechanics() to avoid double-counting in multi-faced cards
    mechanics = card.get_face_mechanics()
    score += len(mechanics) * 3.0

    # 4. Specific High-Complexity Features
    # Modal choices are notoriously complex for beginners
    if 'Modal/Choice' in mechanics:
        score += 5.0

    # X-effects add a layer of mathematical complexity
    if 'X-Cost/Effect' in mechanics:
        score += 4.0

    # "Station" is a high-complexity custom mechanic in this toolkit
    if "station" in text.lower():
        score += 6.0

    # 5. Multi-face cards (recursive scoring)
    if card.bside:
        # Add 5 points for the overhead of having a second side, plus its own complexity
        score += 5.0 + calculate_complexity_score(card.bside)

    return score

def main():
    parser = argparse.ArgumentParser(
        description="Analyze and rank Magic: The Gathering cards by their heuristic 'Complexity Score'.",
        epilog='''
Complexity Score factors include:
  - Rules text length and line count.
  - Presence of keyword abilities and recognized mechanics.
  - Structural features like modal choices, X-costs, and multiple faces.
  - Custom mechanics like 'Station'.

This tool helps identify 'NWO violations' (overly complex commons) and
profiles the complexity curve of a set.
''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, XML, or encoded text). Defaults to stdin (-).')
    io_group.add_argument('--json', action='store_true',
                        help='Output complexity data as JSON.')

    # Group: Analysis Options
    analysis_group = parser.add_argument_group('Analysis Options')
    analysis_group.add_argument('-t', '--top', type=int, default=15,
                                help='Number of most complex cards to display (Default: 15).')
    analysis_group.add_argument('--nwo-threshold', type=int, default=15,
                                help='Score threshold for flagged "NWO Violation" commons (Default: 15).')

    # Group: Filtering Options (Standard)
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('--grep', action='append', help='Only include cards matching a search pattern.')
    filter_group.add_argument('--vgrep', '--exclude', action='append', dest='vgrep', help='Exclude cards matching a search pattern.')
    filter_group.add_argument('--set', action='append', help='Only include cards from specific sets.')
    filter_group.add_argument('--rarity', action='append', help='Only include cards of specific rarities.')
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
    elif args.color is None and sys.stdout.isatty() and not args.json:
        use_color = True

    # Load and filter cards
    cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose,
                                  grep=args.grep, vgrep=args.vgrep,
                                  sets=args.set, rarities=args.rarity)

    if args.limit > 0:
        cards = cards[:args.limit]

    if not cards:
        if not args.quiet:
            print("No cards found matching the criteria.", file=sys.stderr)
        return

    # Analyze complexity
    results = []
    rarity_stats = defaultdict(list)
    nwo_violations = []

    for card in cards:
        score = calculate_complexity_score(card)
        results.append({
            'name': titlecase(card.name),
            'rarity': card.rarity_name,
            'score': score,
            'mechanics': sorted(list(card.mechanics))
        })

        rarity_stats[card.rarity_name.lower()].append(score)

        # Check for NWO violation (Complex Commons)
        if card.rarity == utils.rarity_common_marker and score >= args.nwo_threshold:
            nwo_violations.append((titlecase(card.name), score))

    # Sort by score descending
    results.sort(key=lambda x: x['score'], reverse=True)

    if args.json:
        output = {
            'cards': results,
            'rarity_averages': {r: sum(scores)/len(scores) for r, scores in rarity_stats.items() if scores},
            'nwo_violations': [{'name': name, 'score': score} for name, score in nwo_violations]
        }
        print(json.dumps(output, indent=2))
        return

    # Display Top Complex Cards
    header_title = "MOST COMPLEX CARDS"
    if use_color:
        print(utils.colorize(header_title, utils.Ansi.BOLD + utils.Ansi.CYAN + utils.Ansi.UNDERLINE))
    else:
        print(f"=== {header_title} ===")

    header = ["Rank", "Card Name", "Rarity", "Score", "Mechanics"]
    if use_color:
        header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]

    rows = [header]
    for i, res in enumerate(results[:args.top]):
        name = res['name']
        rarity = res['rarity']
        score_val = f"{res['score']:.1f}"
        mechs = ", ".join(res['mechanics'])

        if use_color:
            name = utils.colorize(name, utils.Ansi.BOLD)
            rarity = utils.colorize(rarity, utils.Ansi.get_rarity_color(rarity))
            score_val = utils.colorize(score_val, utils.Ansi.BOLD + (utils.Ansi.RED if res['score'] > 25 else utils.Ansi.YELLOW))
            mechs = utils.colorize(mechs, utils.Ansi.CYAN)

        rows.append([str(i+1), name, rarity, score_val, mechs])

    datalib.add_separator_row(rows)
    datalib.printrows(datalib.padrows(rows, aligns=['r', 'l', 'l', 'r', 'l']), indent=2)
    print()

    # Display Rarity Averages
    header_rarity = "COMPLEXITY BY RARITY"
    if use_color:
        print(utils.colorize(header_rarity, utils.Ansi.BOLD + utils.Ansi.CYAN + utils.Ansi.UNDERLINE))
    else:
        print(f"=== {header_rarity} ===")

    r_header = ["Rarity", "Count", "Avg Score", "Distribution"]
    if use_color:
        r_header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in r_header]

    r_rows = [r_header]
    # Standard rarity order
    for r_name in ['common', 'uncommon', 'rare', 'mythic', 'basic land', 'special']:
        if r_name in rarity_stats:
            scores = rarity_stats[r_name]
            count = len(scores)
            avg = sum(scores) / count

            label = r_name.title()
            avg_str = f"{avg:5.2f}"

            if use_color:
                label = utils.colorize(label, utils.Ansi.get_rarity_color(r_name))
                avg_str = utils.colorize(avg_str, utils.Ansi.BOLD + utils.Ansi.GREEN)

            bar = datalib.get_bar_chart(min(100, avg * 3), use_color) # Scale for display
            r_rows.append([label, str(count), avg_str, bar])

    datalib.add_separator_row(r_rows)
    datalib.printrows(datalib.padrows(r_rows, aligns=['l', 'r', 'r', 'l']), indent=2)
    print()

    # NWO Violations
    if nwo_violations:
        header_nwo = f"NWO COMPLIANCE WARNINGS (Complex Commons > {args.nwo_threshold})"
        if use_color:
            print(utils.colorize(header_nwo, utils.Ansi.BOLD + utils.Ansi.RED + utils.Ansi.UNDERLINE))
        else:
            print(f"!!! {header_nwo} !!!")

        nwo_violations.sort(key=lambda x: x[1], reverse=True)
        for name, score in nwo_violations:
            name_str = name
            score_str = f"({score:.1f})"
            if use_color:
                name_str = utils.colorize(name, utils.Ansi.BOLD + utils.Ansi.RED)
                score_str = utils.colorize(score_str, utils.Ansi.RED)
            print(f"  - {name_str} {score_str}")
        print()

    if not args.quiet:
        utils.print_operation_summary("Complexity Analysis", len(cards), 0, quiet=args.quiet)

if __name__ == "__main__":
    main()
