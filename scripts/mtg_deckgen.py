#!/usr/bin/env python3
import sys
import os
import argparse
import random
import json
import csv
import io
from collections import defaultdict, Counter

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import cardlib
import datalib
import cli_utils

# Add scripts directory to path to allow importing from mtg_manabase
scripts_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(scripts_dir)
from mtg_manabase import calculate_manabase

def get_color_identity_set(card):
    # Returns a set of characters like {'W', 'U'}
    if not hasattr(card, 'color_identity') or not card.color_identity:
        return set()
    return set(card.color_identity.upper())

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

  # Generate a Standard deck with a 15-card sideboard
  python3 scripts/mtg_deckgen.py data/AllPrintings.json --format standard --sideboard

  # Preview deck generation without creating or modifying output files
  python3 scripts/mtg_deckgen.py data/AllPrintings.json --format commander --dry-run

  # Export decklist in JSON or CSV format
  python3 scripts/mtg_deckgen.py data/AllPrintings.json --format standard --json
  python3 scripts/mtg_deckgen.py data/AllPrintings.json --format commander --outfile deck.csv
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, XML, encoded text). '
                             'Defaults to stdin (-) or data/AllPrintings.json if run interactively. '
                             'If this is not a valid path, it is treated as a commander name query.')
    io_group.add_argument('--outfile', help='Output decklist file (.txt or .dec). Prints to stdout if omitted.')

    # Group: Output Format
    fmt_group_title = parser.add_argument_group('Output Format')
    fmt_group = fmt_group_title.add_mutually_exclusive_group()
    fmt_group.add_argument('-j', '--json', action='store_true', help='Export generated decklist in structured JSON format.')
    fmt_group.add_argument('--csv', action='store_true', help='Export generated decklist in CSV format.')

    # Group: Deck Configuration
    deck_group = parser.add_argument_group('Deck Configuration')
    deck_group.add_argument('--format', choices=['commander', 'standard', 'brawl', 'pauper', 'limited'], default='commander',
                            help='Deck format (Default: commander).')
    deck_group.add_argument('--commander', help='Specific legendary creature to use as commander (case-insensitive).')
    deck_group.add_argument('--creatures', type=int, help='Override target number of creatures.')
    deck_group.add_argument('--spells', type=int, help='Override target number of non-creature spells.')
    deck_group.add_argument('--lands', type=int, help='Override target number of lands.')
    deck_group.add_argument('--curve', help='Override mana curve for creatures. Format "1:5,2:10,3:10,4:8,5:5,6+:5"')
    deck_group.add_argument('--sideboard', action='store_true',
                            help='Generate a sideboard for the deck (Default size: 15 for Standard/Pauper/Limited, 10 for Commander/Brawl unless --sideboard-size is specified).')
    deck_group.add_argument('--sideboard-size', type=int,
                            help='Override target number of cards for the sideboard.')

    # Group: Filtering Options (Standard across tools)
    cli_utils.add_standard_filters(parser)

    # Group: Processing & Debugging
    proc_group = parser.add_argument_group('Processing & Debugging')
    proc_group.add_argument('-p', '--preview', '--dry-run', dest='dry_run', action='store_true',
                        help='Print a summary of deck stats (total deck size, format, composition breakdown, and sample preview of up to 10 entries) to standard output without creating or modifying the target output file.')
    proc_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    proc_group.add_argument('-q', '--quiet', action='store_true', help='Suppress non-critical status messages.')
    
    # Color options
    color_group = proc_group.add_mutually_exclusive_group()
    color_group.add_argument('--color', action='store_true', default=None, help='Force enable ANSI color output.')
    color_group.add_argument('--no-color', action='store_false', dest='color', help='Disable ANSI color output.')

    args = parser.parse_args()

    # UX Improvement: Smart positional argument handling
    if args.infile and args.infile != '-' and not os.path.exists(args.infile) and not args.infile.endswith(('.json', '.csv', '.xml', '.dec', '.txt')):
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

    # Graceful check for dataset requirements in interactive terminal (prevent hangs/misleading errors when default dataset is missing)
    if args.infile == '-' and sys.stdin.isatty():
        parser.print_help()
        print("\nError: Deck generation requires an input dataset or card pool. "
              "Please specify a file or pipe input, or make data/AllPrintings.json available.",
              file=sys.stderr)
        sys.exit(1)

    # Auto-detect export format based on outfile extension if not explicitly specified
    if not (args.json or args.csv):
        if args.outfile:
            if args.outfile.lower().endswith('.json'):
                args.json = True
            elif args.outfile.lower().endswith('.csv'):
                args.csv = True

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
    all_cards = cli_utils.load_and_filter_cards(args)
    
    if args.limit > 0:
        all_cards = all_cards[:args.limit]

    if not all_cards:
        print("Error: No cards found in the card pool matching criteria.", file=sys.stderr)
        sys.exit(1)

    # Filter out basic lands for the main pool
    basic_land_names = ['Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes']
    pool = [c for c in all_cards if c.display_name not in basic_land_names]

    if args.format == 'pauper':
        all_cards = [c for c in all_cards if c.rarity_name.lower() in ('common', 'o')]
        pool = [c for c in pool if c.rarity_name.lower() in ('common', 'o')]
        if not pool:
            print("Error: No common cards found in the card pool for Pauper format.", file=sys.stderr)
            sys.exit(1)
    
    decklist = []
    structured_records = []
    actual_composition = Counter()

    if args.format in ('commander', 'brawl'):
        if args.format == 'commander':
            creatures_target = args.creatures if args.creatures is not None else 30
            spells_target = args.spells if args.spells is not None else 31
            lands_target = args.lands if args.lands is not None else 38
            default_curve = {1: 5, 2: 15, 3: 15, 4: 10, 5: 8, 6: 8}
        else: # brawl
            creatures_target = args.creatures if args.creatures is not None else 18
            spells_target = args.spells if args.spells is not None else 18
            lands_target = args.lands if args.lands is not None else 24
            default_curve = {1: 3, 2: 8, 3: 8, 4: 5, 5: 3, 6: 3}
        
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
            curve = default_curve

        # Identify Commander candidates
        if args.format == 'brawl':
            legendary_candidates = [c for c in pool if any(s.lower() == 'legendary' for s in c.supertypes) and (c.is_creature or c.is_planeswalker)]
        else:
            legendary_candidates = [c for c in pool if any(s.lower() == 'legendary' for s in c.supertypes) and c.is_creature]

        if not legendary_candidates:
            # Fallback if no planeswalkers
            legendary_candidates = [c for c in pool if any(s.lower() == 'legendary' for s in c.supertypes) and c.is_creature]

        if not legendary_candidates:
            print("Error: No legendary commanders found in the filtered card pool.", file=sys.stderr)
            sys.exit(1)
            
        commander_card = None
        if args.commander:
            matches = [c for c in legendary_candidates if c.display_name.lower() == args.commander.lower()]
            if matches:
                commander_card = matches[0]
            else:
                if not args.quiet:
                    print(f"Warning: Commander '{args.commander}' not found. Picking a random one.", file=sys.stderr)
                
        if not commander_card:
            commander_card = random.choice(legendary_candidates)
            
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
            if get_color_identity_set(c).issubset(cmd_id):
                valid_pool.append(c)
                
        creatures_pool = [c for c in valid_pool if c.is_creature]
        spells_pool = [c for c in valid_pool if not c.is_creature and not c.is_land]
        
        deck_creatures = pick_cards_with_curve(creatures_pool, creatures_target, curve=curve)
        deck_spells = pick_cards_with_curve(spells_pool, spells_target)
        
        deck_lands = []
        spells_for_manabase = [commander_card] + deck_creatures + deck_spells
        recommendation, _, _ = calculate_manabase(spells_for_manabase, lands_target)
        for land, count in recommendation.items():
            if count > 0:
                deck_lands.extend([land] * count)
            
        decklist.append(f"1 {commander_card.display_name} *CMDR*")
        actual_composition['Commander'] = 1
        cmc_val = float(commander_card.cost.cmc) if hasattr(commander_card, 'cost') and hasattr(commander_card.cost, 'cmc') else 0.0
        type_line = commander_card.type_line if hasattr(commander_card, 'type_line') else getattr(commander_card, 'types_str', 'Creature')
        set_str = commander_card.set_code.upper() if getattr(commander_card, 'set_code', None) else ''
        structured_records.append({
            'count': 1,
            'name': commander_card.display_name,
            'section': 'Commander',
            'category': 'Commander',
            'type': type_line,
            'cmc': cmc_val,
            'set': set_str
        })
        
        for c in deck_creatures:
            decklist.append(f"1 {c.display_name}")
            actual_composition['Creatures'] += 1
            cmc_val = float(c.cost.cmc) if hasattr(c, 'cost') and hasattr(c.cost, 'cmc') else 0.0
            type_line = c.type_line if hasattr(c, 'type_line') else getattr(c, 'types_str', 'Creature')
            set_str = c.set_code.upper() if getattr(c, 'set_code', None) else ''
            structured_records.append({
                'count': 1,
                'name': c.display_name,
                'section': 'Maindeck',
                'category': 'Creature',
                'type': type_line,
                'cmc': cmc_val,
                'set': set_str
            })

        for c in deck_spells:
            decklist.append(f"1 {c.display_name}")
            actual_composition['Spells'] += 1
            cmc_val = float(c.cost.cmc) if hasattr(c, 'cost') and hasattr(c.cost, 'cmc') else 0.0
            type_line = c.type_line if hasattr(c, 'type_line') else getattr(c, 'types_str', 'Spell')
            set_str = c.set_code.upper() if getattr(c, 'set_code', None) else ''
            structured_records.append({
                'count': 1,
                'name': c.display_name,
                'section': 'Maindeck',
                'category': 'Spell',
                'type': type_line,
                'cmc': cmc_val,
                'set': set_str
            })
            
        land_counts = Counter(deck_lands)
        for l, count in sorted(land_counts.items()):
            decklist.append(f"{count} {l}")
            actual_composition['Lands'] += count
            structured_records.append({
                'count': count,
                'name': l,
                'section': 'Maindeck',
                'category': 'Land',
                'type': 'Basic Land',
                'cmc': 0.0,
                'set': ''
            })

        # Determine sideboard size for Commander/Brawl
        if args.sideboard_size is not None:
            sideboard_target = max(0, args.sideboard_size)
        elif args.sideboard:
            sideboard_target = 10
        else:
            sideboard_target = 0

        if sideboard_target > 0:
            used_main = set(deck_creatures + deck_spells)
            side_candidates = [c for c in valid_pool if c not in used_main]
            if len(side_candidates) < sideboard_target:
                side_cards = list(side_candidates)
                needed = sideboard_target - len(side_cards)
                if valid_pool:
                    side_cards.extend(random.choices(valid_pool, k=needed))
            else:
                side_cards = random.sample(side_candidates, sideboard_target)

            if side_cards:
                decklist.append("")
                decklist.append("Sideboard")
                for c in side_cards:
                    decklist.append(f"1 {c.display_name}")
                    cmc_val = float(c.cost.cmc) if hasattr(c, 'cost') and hasattr(c.cost, 'cmc') else 0.0
                    type_line = c.type_line if hasattr(c, 'type_line') else getattr(c, 'types_str', 'Card')
                    set_str = c.set_code.upper() if getattr(c, 'set_code', None) else ''
                    structured_records.append({
                        'count': 1,
                        'name': c.display_name,
                        'section': 'Sideboard',
                        'category': 'Sideboard',
                        'type': type_line,
                        'cmc': cmc_val,
                        'set': set_str
                    })
                actual_composition['Sideboard'] = len(side_cards)

    elif args.format in ('standard', 'pauper', 'limited'):
        if args.format == 'limited':
            creatures_target = args.creatures if args.creatures is not None else 15
            spells_target = args.spells if args.spells is not None else 8
            lands_target = args.lands if args.lands is not None else 17
        else: # standard / pauper
            creatures_target = args.creatures if args.creatures is not None else 20
            spells_target = args.spells if args.spells is not None else 16
            lands_target = args.lands if args.lands is not None else 24
        
        creatures_pool = [c for c in pool if c.is_creature]
        spells_pool = [c for c in pool if not c.is_creature and not c.is_land]
        
        if not creatures_pool and creatures_target > 0:
            if not args.quiet:
                print(f"Warning: No creatures found in pool for {args.format} deck.", file=sys.stderr)
            creatures_target = 0

        if not spells_pool and spells_target > 0:
            if not args.quiet:
                print(f"Warning: No non-creature spells found in pool for {args.format} deck.", file=sys.stderr)
            spells_target = 0

        chosen_cards = []
        
        if creatures_target > 0:
            # In standard, we allow multiple copies, so we sample a smaller unique pool and then repeat
            # Heuristic: about 4-of each unique card (or 2-of for limited)
            divisor = 2 if args.format == 'limited' else 4
            c_sample = pick_cards_with_curve(creatures_pool, max(1, creatures_target // divisor))
            if c_sample:
                for _ in range(creatures_target):
                    chosen_cards.append(random.choice(c_sample))
            
        if spells_target > 0:
            divisor = 2 if args.format == 'limited' else 4
            s_sample = pick_cards_with_curve(spells_pool, max(1, spells_target // divisor))
            if s_sample:
                for _ in range(spells_target):
                    chosen_cards.append(random.choice(s_sample))
            
        grouped = Counter([c.display_name for c in chosen_cards])

        # Basic land distribution using calculate_manabase
        recommendation, _, _ = calculate_manabase(chosen_cards, lands_target)
        for land, count in recommendation.items():
            if count > 0:
                grouped[land] += count
            
        basics_to_add = ['Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes']
        # Map card metadata for chosen_cards
        card_meta_map = {}
        for c in chosen_cards:
            if c.display_name not in card_meta_map:
                cmc_val = float(c.cost.cmc) if hasattr(c, 'cost') and hasattr(c.cost, 'cmc') else 0.0
                type_line = c.type_line if hasattr(c, 'type_line') else getattr(c, 'types_str', 'Card')
                cat = 'Creature' if getattr(c, 'is_creature', False) else 'Spell'
                set_str = c.set_code.upper() if getattr(c, 'set_code', None) else ''
                card_meta_map[c.display_name] = {'category': cat, 'type': type_line, 'cmc': cmc_val, 'set': set_str}

        for name, count in sorted(grouped.items()):
            decklist.append(f"{count} {name}")
            if name in basics_to_add:
                actual_composition['Lands'] += count
                meta = {'category': 'Land', 'type': 'Basic Land', 'cmc': 0.0, 'set': ''}
            else:
                meta = card_meta_map.get(name, {'category': 'Card', 'type': 'Card', 'cmc': 0.0, 'set': ''})

            structured_records.append({
                'count': count,
                'name': name,
                'section': 'Maindeck',
                'category': meta['category'],
                'type': meta['type'],
                'cmc': meta['cmc'],
                'set': meta['set']
            })
        
        actual_composition['Creatures'] = creatures_target
        actual_composition['Spells'] = spells_target

        # Determine sideboard size for Standard/Pauper/Limited
        if args.sideboard_size is not None:
            sideboard_target = max(0, args.sideboard_size)
        elif args.sideboard:
            sideboard_target = 15
        else:
            sideboard_target = 0

        if sideboard_target > 0:
            valid_spells_and_creatures = creatures_pool + spells_pool
            if valid_spells_and_creatures:
                divisor = 2 if args.format == 'limited' else 4
                side_sample_count = max(1, sideboard_target // divisor)
                unused_cards = [c for c in valid_spells_and_creatures if c not in chosen_cards]
                side_candidates = unused_cards if unused_cards else valid_spells_and_creatures
                side_sample = random.sample(side_candidates, min(side_sample_count, len(side_candidates)))
                side_chosen = []
                for _ in range(sideboard_target):
                    side_chosen.append(random.choice(side_sample))

                side_grouped = Counter([c.display_name for c in side_chosen])
                side_meta_map = {}
                for c in side_chosen:
                    if c.display_name not in side_meta_map:
                        cmc_val = float(c.cost.cmc) if hasattr(c, 'cost') and hasattr(c.cost, 'cmc') else 0.0
                        type_line = c.type_line if hasattr(c, 'type_line') else getattr(c, 'types_str', 'Card')
                        set_str = c.set_code.upper() if getattr(c, 'set_code', None) else ''
                        side_meta_map[c.display_name] = {'type': type_line, 'cmc': cmc_val, 'set': set_str}

                decklist.append("")
                decklist.append("Sideboard")
                for name, count in sorted(side_grouped.items()):
                    decklist.append(f"{count} {name}")
                    meta = side_meta_map.get(name, {'type': 'Card', 'cmc': 0.0, 'set': ''})
                    structured_records.append({
                        'count': count,
                        'name': name,
                        'section': 'Sideboard',
                        'category': 'Sideboard',
                        'type': meta['type'],
                        'cmc': meta['cmc'],
                        'set': meta['set']
                    })
                actual_composition['Sideboard'] = sum(side_grouped.values())

    total_deck_size = sum(actual_composition.values())

    if getattr(args, 'dry_run', False):
        fmt_desc = "JSON" if args.json else ("CSV" if args.csv else "Text")
        print(f"Dry Run Summary: Generated {total_deck_size}-card deck ({args.format.capitalize()} format, Output: {fmt_desc}).")
        if args.format in ('commander', 'brawl') and 'commander_card' in locals() and commander_card:
            print(f"Commander: {commander_card.display_name}")
        print("Composition Breakdown:")
        for cat in sorted(actual_composition.keys()):
            print(f"  {cat}: {actual_composition[cat]}")
        sample_entries = decklist[:10]
        print(f"Sample Preview (up to 10 entries):\n  " + "\n  ".join(sample_entries))
        return

    # Final Summary to stderr
    if not args.quiet:
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

    # Prepare formatted export content
    if args.json:
        export_data = {
            'format': args.format,
            'total_cards': total_deck_size,
            'composition': dict(actual_composition),
            'deck': structured_records
        }
        out_content = json.dumps(export_data, indent=2) + "\n"
    elif args.csv:
        csv_buf = io.StringIO()
        fieldnames = ['count', 'name', 'section', 'category', 'type', 'cmc', 'set']
        writer = csv.DictWriter(csv_buf, fieldnames=fieldnames)
        writer.writeheader()
        for rec in structured_records:
            writer.writerow(rec)
        out_content = csv_buf.getvalue()
    else:
        out_content = "\n".join(decklist) + "\n"

    # Output Decklist
    if args.outfile:
        with open(args.outfile, 'w', encoding='utf-8') as f:
            f.write(out_content)
        if not args.quiet:
            print(f"Decklist saved to {args.outfile}", file=sys.stderr)
    else:
        if not args.quiet and not (args.json or args.csv):
            print("--- Decklist ---", file=sys.stderr)
        sys.stderr.flush()
        print(out_content, end="")

if __name__ == '__main__':
    main()
