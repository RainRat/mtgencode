#!/usr/bin/env python3
import sys
import os
import argparse
import random
from collections import defaultdict

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import jdecode

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
    
    for cmc, count in curve.items():
        if count <= 0: continue
        available = by_cmc.get(cmc, [])
        if cmc >= 6:
            available = []
            for k, v in by_cmc.items():
                if k >= 6:
                    available.extend(v)
        
        pick_count = min(count, len(available))
        if pick_count > 0:
            chosen = random.sample(available, pick_count)
            picked.extend(chosen)
            for ch in chosen:
                for k, v in by_cmc.items():
                    if ch in v:
                        v.remove(ch)
    
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
        description="Generate a complete MTG deck from a card pool.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Generate a Commander deck with a random commander from a pool
  python3 scripts/mtg_deckgen.py data/AllPrintings.json --format commander

  # Generate a Commander deck with a specific commander
  python3 scripts/mtg_deckgen.py data/AllPrintings.json --commander "Atraxa, Praetors' Voice"

  # Generate a Standard deck from a pool
  python3 scripts/mtg_deckgen.py data/AllPrintings.json --format standard

  # Override deck composition (e.g., more lands, fewer creatures)
  python3 scripts/mtg_deckgen.py data/AllPrintings.json --creatures 20 --spells 30 --lands 40

  # Override mana curve for creatures (Format: "CMC:Count,CMC:Count,...")
  python3 scripts/mtg_deckgen.py data/AllPrintings.json --curve "1:5,2:10,3:10,4:8,5:5,6+:5"

  # Save the decklist to a file
  python3 scripts/mtg_deckgen.py data/AllPrintings.json --outfile my_deck.txt
"""
    )

    parser.add_argument('infile', help='Input card data (JSON, CSV, XML, encoded text).')
    parser.add_argument('--format', choices=['commander', 'standard'], default='commander', help='Deck format (Default: commander).')
    parser.add_argument('--commander', help='Specific legendary creature to use as commander (case-insensitive).')
    
    # Distribution overrides
    parser.add_argument('--creatures', type=int, help='Override target number of creatures.')
    parser.add_argument('--spells', type=int, help='Override target number of non-creature spells.')
    parser.add_argument('--lands', type=int, help='Override target number of lands.')
    parser.add_argument('--curve', help='Override mana curve. Format "1:5,2:10,3:10,4:8,5:5,6+:5"')
    
    parser.add_argument('--outfile', help='Output decklist file (.txt or .dec). Prints to stdout if omitted.')

    args = parser.parse_args()

    if not args.infile:
        print("Error: Input file required.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Loading cards from {args.infile}...", file=sys.stderr)
    all_cards = jdecode.mtg_open_file(args.infile, verbose=False)
    
    # Capitalize names for easier filtering
    basic_land_names = ['Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes']
    pool = [c for c in all_cards if c.name.title() not in basic_land_names]
    
    if args.format == 'commander':
        creatures_target = args.creatures if args.creatures is not None else 30
        spells_target = args.spells if args.spells is not None else 31
        lands_target = args.lands if args.lands is not None else 38
        
        curve = None
        if args.curve:
            curve = {}
            for p in args.curve.split(','):
                k, v = p.split(':')
                if k.endswith('+'):
                    curve[int(k[:-1])] = int(v)
                else:
                    curve[int(k)] = int(v)
        else:
            curve = {1: 5, 2: 15, 3: 15, 4: 10, 5: 8, 6: 8} 

        legendary_creatures = [c for c in pool if any(s.lower() == 'legendary' for s in getattr(c, 'supertypes', [])) and any(t.lower() == 'creature' for t in getattr(c, 'types', []))]
        if not legendary_creatures:
            print("Error: No legendary creatures found in the input pool.", file=sys.stderr)
            sys.exit(1)
            
        commander_card = None
        if args.commander:
            matches = [c for c in legendary_creatures if c.name.lower() == args.commander.lower()]
            if matches:
                commander_card = matches[0]
            else:
                print(f"Warning: Commander '{args.commander}' not found. Picking a random one.", file=sys.stderr)
                
        if not commander_card:
            commander_card = random.choice(legendary_creatures)
            
        cmd_id = get_color_identity_set(commander_card)
        cmd_id_str = "".join(sorted(list(cmd_id))) if cmd_id else "Colorless"
        print(f"Commander: {commander_card.name.title()} (Identity: {cmd_id_str})", file=sys.stderr)
        
        valid_pool = []
        for c in pool:
            if c.name == commander_card.name: continue
            if subset_identity(get_color_identity_set(c), cmd_id):
                valid_pool.append(c)
                
        creatures_pool = [c for c in valid_pool if any(t.lower() == 'creature' for t in getattr(c, 'types', []))]
        spells_pool = [c for c in valid_pool if not any(t.lower() == 'creature' for t in getattr(c, 'types', [])) and not any(t.lower() == 'land' for t in getattr(c, 'types', []))]
        
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
            
        decklist = []
        decklist.append(f"1 {commander_card.name.title()} *CMDR*")
        
        for c in deck_creatures:
            decklist.append(f"1 {c.name.title()}")
        for c in deck_spells:
            decklist.append(f"1 {c.name.title()}")
            
        land_counts = defaultdict(int)
        for l in deck_lands:
            land_counts[l] += 1
            
        for l, count in land_counts.items():
            decklist.append(f"{count} {l}")
            
        out_text = "\n".join(decklist) + "\n"
        if args.outfile:
            with open(args.outfile, 'w', encoding='utf-8') as f:
                f.write(out_text)
            print(f"Decklist saved to {args.outfile}", file=sys.stderr)
        else:
            print("\n--- Decklist ---")
            print(out_text)
            
    elif args.format == 'standard':
        creatures_target = args.creatures if args.creatures is not None else 20
        spells_target = args.spells if args.spells is not None else 16
        lands_target = args.lands if args.lands is not None else 24
        
        creatures_pool = [c for c in pool if any(t.lower() == 'creature' for t in getattr(c, 'types', []))]
        spells_pool = [c for c in pool if not any(t.lower() == 'creature' for t in getattr(c, 'types', [])) and not any(t.lower() == 'land' for t in getattr(c, 'types', []))]
        
        c_sample = pick_cards_with_curve(creatures_pool, max(1, creatures_target // 4))
        s_sample = pick_cards_with_curve(spells_pool, max(1, spells_target // 4))
        
        decklist = []
        
        if creatures_target > 0:
            if not c_sample:
                print("Warning: No creatures found in pool for standard deck.", file=sys.stderr)
            else:
                for i in range(creatures_target):
                    decklist.append(random.choice(c_sample).name.title())
            
        if spells_target > 0:
            if not s_sample:
                print("Warning: No non-creature spells found in pool for standard deck.", file=sys.stderr)
            else:
                for i in range(spells_target):
                    decklist.append(random.choice(s_sample).name.title())
            
        grouped = defaultdict(int)
        for name in decklist:
            grouped[name] += 1
            
        deck_lands = []
        basics_to_add = ['Plains', 'Island', 'Swamp', 'Mountain', 'Forest']
        land_choices = random.sample(basics_to_add, 2)
        for i in range(lands_target):
            deck_lands.append(random.choice(land_choices))
            
        for l in deck_lands:
            grouped[l] += 1
            
        out_text = "\n".join([f"{v} {k}" for k,v in grouped.items()]) + "\n"
        
        if args.outfile:
            with open(args.outfile, 'w', encoding='utf-8') as f:
                f.write(out_text)
            print(f"Decklist saved to {args.outfile}", file=sys.stderr)
        else:
            print("\n--- Decklist ---")
            print(out_text)

    else:
        print("Format not supported.", file=sys.stderr)

if __name__ == '__main__':
    main()
