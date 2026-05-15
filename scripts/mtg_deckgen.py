#!/usr/bin/env python3
import sys
import os
import argparse
import random
from collections import defaultdict, Counter

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import cardlib
import datalib

def get_color_identity_set(card):
    # Returns a set of characters like {'W', 'U'}
    if not hasattr(card, 'color_identity') or not card.color_identity:
        return set()
    return set(card.color_identity.upper())

def subset_identity(card_id, cmd_id):
    # Returns True if card_id is a subset of cmd_id
    return card_id.issubset(cmd_id)

def pick_cards_with_curve(pool, target_count, curve=None):
    if not pool:
        return []
    
    if not curve:
        if len(pool) < target_count:
            return pool.copy()
        return random.sample(pool, target_count)
    
    by_cmc = defaultdict(list)
    for c in pool:
        try:
            cmc = int(float(c.cost.cmc))
        except (ValueError, TypeError):
            cmc = 0
        by_cmc[cmc].append(c)
        
    picked = []
    
    # Sort curve keys to ensure consistent order if multiple CMC match 6+
    sorted_cmcs = sorted(curve.keys())

    for cmc in sorted_cmcs:
        count = curve[cmc]
        if count <= 0: continue

        available = []
        if cmc >= 6:
            # Aggregate all 6+ for the high end of the curve
            for k, v in by_cmc.items():
                if k >= 6:
                    available.extend(v)
        else:
            available = by_cmc.get(cmc, [])
        
        pick_count = min(count, len(available))
        if pick_count > 0:
            chosen = random.sample(available, pick_count)
            picked.extend(chosen)
            # Remove chosen cards from the by_cmc pools so they aren't picked twice
            for ch in chosen:
                for k in list(by_cmc.keys()):
                    if ch in by_cmc[k]:
                        by_cmc[k].remove(ch)
    
    remaining_target = target_count - len(picked)
    if remaining_target > 0:
        remaining_pool = []
        for v in by_cmc.values():
            remaining_pool.extend(v)
        
        if remaining_pool:
            fill_count = min(remaining_target, len(remaining_pool))
            picked.extend(random.sample(remaining_pool, fill_count))
            
    return picked

def main():
    parser = argparse.ArgumentParser(
        description="Generate a complete Magic: The Gathering deck from a card pool. "
                    "Optimized for design evaluation and quick playtesting.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Generate a Commander deck with a random commander from a pool
  python3 scripts/mtg_deckgen.py data/AllPrintings.json --format commander

  # Quickly generate a deck using the default dataset and a specific commander
  python3 scripts/mtg_deckgen.py "Atraxa, Praetors' Voice"

  # Generate a Standard deck from a pool
  python3 scripts/mtg_deckgen.py data/AllPrintings.json --format standard

  # Override deck composition (e.g., more lands, fewer creatures)
  python3 scripts/mtg_deckgen.py data/AllPrintings.json --creatures 20 --spells 30 --lands 40

  # Override mana curve for creatures (Format: "CMC:Count,CMC:Count,...")
  python3 scripts/mtg_deckgen.py data/AllPrintings.json --curve "1:5,2:10,3:10,4:8,5:5,6+:5"

  # Filter the card pool (e.g., only Goblins)
  python3 scripts/mtg_deckgen.py data/AllPrintings.json --grep "Goblin"

  # Save the decklist to a file
  python3 scripts/mtg_deckgen.py data/AllPrintings.json --outfile my_deck.txt
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, XML, encoded text). '
                             'Defaults to stdin (-) or data/AllPrintings.json if run interactively. '
                             'If this is not a valid path, it is treated as a commander name query.')
    io_group.add_argument('--outfile', help='Output decklist file (.txt or .dec). Prints to stdout if omitted.')

    # Group: Deck Configuration
    deck_group = parser.add_argument_group('Deck Configuration')
    deck_group.add_argument('--format', choices=['commander', 'standard'], default='commander',
                            help='Deck format (Default: commander).')
    deck_group.add_argument('--commander', help='Specific legendary creature to use as commander (case-insensitive).')
    deck_group.add_argument('--creatures', type=int, help='Override target number of creatures.')
    deck_group.add_argument('--spells', type=int, help='Override target number of non-creature spells.')
    deck_group.add_argument('--lands', type=int, help='Override target number of lands.')
    deck_group.add_argument('--curve', help='Override mana curve for creatures. Format "1:5,2:10,3:10,4:8,5:5,6+:5"')

    # Group: Filtering Options (Standard across tools)
    filter_group = parser.add_argument_group('Filtering Options')
    filter_group.add_argument('-g', '--grep', action='append',
                        help='Only include cards matching a search pattern (checks name, typeline, text, cost, and stats). Use multiple times for AND logic.')
    filter_group.add_argument('--vgrep', '--exclude', action='append', dest='vgrep',
                        help='Skip cards matching a search pattern. Use multiple times for OR logic.')
    filter_group.add_argument('--set', action='append',
                        help='Only include cards from specific sets.')
    filter_group.add_argument('--rarity', action='append',
                        help="Only include cards of specific rarities (e.g., 'common', 'mythic').")
    filter_group.add_argument('--colors', action='append',
                        help="Only include cards of specific colors (W, U, B, R, G). Use 'C' or 'A' for colorless.")
    filter_group.add_argument('--identity', action='append',
                        help="Only include cards with specific colors in their color identity.")
    filter_group.add_argument('--cmc', action='append',
                        help='Only include cards with specific CMC values (e.g., ">3", "2-4").')
    filter_group.add_argument('--pow', '--power', action='append', dest='pow',
                        help='Only include cards with specific Power values.')
    filter_group.add_argument('--tou', '--toughness', action='append', dest='tou',
                        help='Only include cards with specific Toughness values.')
    filter_group.add_argument('--loy', '--loyalty', '--defense', action='append', dest='loy',
                        help='Only include cards with specific Loyalty or Defense values.')
    filter_group.add_argument('--mechanic', action='append',
                        help='Only include cards with specific mechanical features (e.g., Flying, ETB Effect).')

    # Group: Processing & Debugging
    proc_group = parser.add_argument_group('Processing & Debugging')
    proc_group.add_argument('-n', '--limit', type=int, default=0, help='Limit input pool to first N cards.')
    proc_group.add_argument('--shuffle', action='store_true', help='Shuffle the input pool before selection.')
    proc_group.add_argument('--seed', type=int, help='Seed for the random number generator.')
    proc_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    proc_group.add_argument('-q', '--quiet', action='store_true', help='Suppress non-critical status messages.')
    
    # Color options
    color_group = proc_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color output.')

    args = parser.parse_args()

    # UX Improvement: Smart positional argument handling
    if args.infile and args.infile != '-' and not os.path.exists(args.infile):
        # Treat as commander query
        if not args.commander:
            args.commander = args.infile
        args.infile = '-'

    # UX Improvement: Default Dataset
    if args.infile == '-' and sys.stdin.isatty():
        script_dir = os.path.dirname(os.path.realpath(__file__))
        default_data = os.path.join(script_dir, '../data/AllPrintings.json')
        if os.path.exists(default_data):
            args.infile = default_data
            if not args.quiet:
                print(f"Notice: Using default dataset: {args.infile}", file=sys.stderr)
        elif os.path.exists('data/AllPrintings.json'):
            args.infile = 'data/AllPrintings.json'
            if not args.quiet:
                print(f"Notice: Using default dataset: {args.infile}", file=sys.stderr)

    # Determine if we should use color
    use_color = False
    if args.color is True:
        use_color = True
    elif args.color is None and sys.stderr.isatty():
        use_color = True

    if args.seed is not None:
        random.seed(args.seed)

    if not args.quiet:
        print(f"Loading cards from {args.infile}...", file=sys.stderr)

    # Load and filter cards
    all_cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose,
                                     grep=args.grep, vgrep=args.vgrep,
                                     sets=args.set, rarities=args.rarity,
                                     colors=args.colors, cmcs=args.cmc,
                                     pows=args.pow, tous=args.tou, loys=args.loy,
                                     mechanics=args.mechanic,
                                     identities=args.identity,
                                     shuffle=args.shuffle, seed=args.seed)
    
    if args.limit > 0:
        all_cards = all_cards[:args.limit]

    if not all_cards:
        print("Error: No cards found in the card pool matching criteria.", file=sys.stderr)
        sys.exit(1)

    # Filter out basic lands for the main pool
    basic_land_names = ['Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes']
    pool = [c for c in all_cards if c.display_name not in basic_land_names]
    
    decklist = []
    actual_composition = Counter()

    if args.format == 'commander':
        creatures_target = args.creatures if args.creatures is not None else 30
        spells_target = args.spells if args.spells is not None else 31
        lands_target = args.lands if args.lands is not None else 38
        
        curve = None
        if args.curve:
            curve = {}
            for p in args.curve.split(','):
                try:
                    k, v = p.split(':')
                    if k.endswith('+'):
                        curve[int(k[:-1])] = int(v)
                    else:
                        curve[int(k)] = int(v)
                except ValueError:
                    if not args.quiet:
                        print(f"Warning: Invalid curve segment '{p}', skipping.", file=sys.stderr)
        else:
            # Default Commander Curve
            curve = {1: 5, 2: 15, 3: 15, 4: 10, 5: 8, 6: 8} 

        # Identify Commander candidates
        legendary_creatures = [c for c in pool if any(s.lower() == 'legendary' for s in c.supertypes) and c.is_creature]
        if not legendary_creatures:
            print("Error: No legendary creatures found in the filtered card pool.", file=sys.stderr)
            sys.exit(1)
            
        commander_card = None
        if args.commander:
            matches = [c for c in legendary_creatures if c.display_name.lower() == args.commander.lower()]
            if matches:
                commander_card = matches[0]
            else:
                if not args.quiet:
                    print(f"Warning: Commander '{args.commander}' not found. Picking a random one.", file=sys.stderr)
                
        if not commander_card:
            commander_card = random.choice(legendary_creatures)
            
        cmd_id = get_color_identity_set(commander_card)
        cmd_id_str = "".join(sorted(list(cmd_id))) if cmd_id else "Colorless"

        if not args.quiet:
            c_name = utils.colorize(commander_card.display_name, commander_card._get_ansi_color()) if use_color else commander_card.display_name
            id_val = cmd_id_str
            if use_color:
                id_val = "".join([utils.colorize(c, utils.Ansi.get_color_color(c)) for c in cmd_id_str])
            print(f"Commander: {c_name} (Identity: {id_val})", file=sys.stderr)
        
        valid_pool = []
        for c in pool:
            if c.display_name == commander_card.display_name: continue
            if subset_identity(get_color_identity_set(c), cmd_id):
                valid_pool.append(c)
                
        creatures_pool = [c for c in valid_pool if c.is_creature]
        spells_pool = [c for c in valid_pool if not c.is_creature and not c.is_land]
        
        deck_creatures = pick_cards_with_curve(creatures_pool, creatures_target, curve=curve)
        deck_spells = pick_cards_with_curve(spells_pool, spells_target)
        
        deck_lands = []
        basics_to_add = []
        if 'W' in cmd_id: basics_to_add.append('Plains')
        if 'U' in cmd_id: basics_to_add.append('Island')
        if 'B' in cmd_id: basics_to_add.append('Swamp')
        if 'R' in cmd_id: basics_to_add.append('Mountain')
        if 'G' in cmd_id: basics_to_add.append('Forest')
        
        if not basics_to_add:
            basics_to_add.append('Wastes')
            
        for i in range(lands_target):
            deck_lands.append(random.choice(basics_to_add))
            
        decklist.append(f"1 {commander_card.display_name} *CMDR*")
        actual_composition['Commander'] = 1
        
        for c in deck_creatures:
            decklist.append(f"1 {c.display_name}")
            actual_composition['Creatures'] += 1
        for c in deck_spells:
            decklist.append(f"1 {c.display_name}")
            actual_composition['Spells'] += 1
            
        land_counts = Counter(deck_lands)
        for l, count in sorted(land_counts.items()):
            decklist.append(f"{count} {l}")
            actual_composition['Lands'] += count
            
    elif args.format == 'standard':
        creatures_target = args.creatures if args.creatures is not None else 20
        spells_target = args.spells if args.spells is not None else 16
        lands_target = args.lands if args.lands is not None else 24
        
        creatures_pool = [c for c in pool if c.is_creature]
        spells_pool = [c for c in pool if not c.is_creature and not c.is_land]
        
        if not creatures_pool and creatures_target > 0:
            if not args.quiet:
                print("Warning: No creatures found in pool for standard deck.", file=sys.stderr)
            creatures_target = 0

        if not spells_pool and spells_target > 0:
            if not args.quiet:
                print("Warning: No non-creature spells found in pool for standard deck.", file=sys.stderr)
            spells_target = 0

        raw_decklist = []
        
        if creatures_target > 0:
            # In standard, we allow multiple copies, so we sample a smaller unique pool and then repeat
            # Heuristic: about 4-of each unique card
            c_sample = pick_cards_with_curve(creatures_pool, max(1, creatures_target // 4))
            if c_sample:
                for i in range(creatures_target):
                    raw_decklist.append(random.choice(c_sample).display_name)
            
        if spells_target > 0:
            s_sample = pick_cards_with_curve(spells_pool, max(1, spells_target // 4))
            if s_sample:
                for i in range(spells_target):
                    raw_decklist.append(random.choice(s_sample).display_name)
            
        grouped = Counter(raw_decklist)

        # Basic land distribution
        basics_to_add = ['Plains', 'Island', 'Swamp', 'Mountain', 'Forest']
        # Pick 2 colors at random for standard deck unless filtered
        land_choices = random.sample(basics_to_add, 2)
        for i in range(lands_target):
            l = random.choice(land_choices)
            grouped[l] += 1
            
        for name, count in sorted(grouped.items()):
            decklist.append(f"{count} {name}")
            if name in basics_to_add:
                actual_composition['Lands'] += count
        
        actual_composition['Creatures'] = creatures_target
        actual_composition['Spells'] = spells_target

    # Final Summary to stderr
    if not args.quiet:
        total_deck_size = sum(actual_composition.values())
        utils.print_header("DECK GENERATED", count=total_deck_size, file=sys.stderr, use_color=use_color)
        summary_rows = []
        # Sort keys for consistent output
        for cat in sorted(actual_composition.keys()):
            count = actual_composition[cat]
            cat_str = cat
            if use_color:
                cat_str = utils.colorize(cat, utils.Ansi.BOLD + utils.Ansi.CYAN)
            summary_rows.append([f"  {cat_str}:", str(count)])

        for row in datalib.padrows(summary_rows, aligns=['l', 'r']):
            print(row, file=sys.stderr)
        print(file=sys.stderr)

    # Output Decklist
    out_text = "\n".join(decklist) + "\n"
    if args.outfile:
        with open(args.outfile, 'w', encoding='utf-8') as f:
            f.write(out_text)
        if not args.quiet:
            print(f"Decklist saved to {args.outfile}", file=sys.stderr)
    else:
        if not args.quiet:
            print("--- Decklist ---", file=sys.stderr)
        print(out_text, end="")

if __name__ == '__main__':
    main()
