#!/usr/bin/env python3
import sys
import os
import argparse
import json
import re

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import cardlib

COLOR_NAME_MAP = {
    'W': 'White',
    'U': 'Blue',
    'B': 'Black',
    'R': 'Red',
    'G': 'Green'
}
LAND_NAME_MAP = {
    'W': 'Plains',
    'U': 'Island',
    'B': 'Swamp',
    'R': 'Mountain',
    'G': 'Forest'
}
COLOR_NAME_TO_SYM = {
    'WHITE': 'W', 'PLAINS': 'W',
    'BLUE': 'U', 'ISLAND': 'U',
    'BLACK': 'B', 'SWAMP': 'B',
    'RED': 'R', 'MOUNTAIN': 'R',
    'GREEN': 'G', 'FOREST': 'G'
}

def adjust_stat(val, amount):
    if val is None:
        return None
    try:
        def repl(match):
            num = int(match.group(0))
            return str(max(0, num + amount))
        return re.sub(r'\d+', repl, str(val))
    except Exception:
        return val

def scale_stat(val, factor, multiply=True):
    if val is None:
        return None
    try:
        def repl(match):
            num = int(match.group(0))
            if multiply:
                new_num = int(round(num * factor))
            else:
                new_num = int(round(num / factor))
            return str(max(1 if not multiply else 0, new_num))
        return re.sub(r'\d+', repl, str(val))
    except Exception:
        return val

def scale_mana_cost(mana_cost, factor, multiply=True):
    if not mana_cost:
        return mana_cost
    def repl(match):
        num = int(match.group(1))
        if multiply:
            new_num = int(round(num * factor))
        else:
            new_num = int(round(num / factor))
        return f"{{{new_num}}}"
    return re.sub(r'\{(\d+)\}', repl, mana_cost)

def apply_color_shift(card_dict, target_colors_str):
    WUBRG = 'WUBRG'

    # 1. Determine original colors
    orig_colors = []
    mana_cost = card_dict.get('manaCost', '')
    if mana_cost:
        for c in 'WUBRG':
            if c in mana_cost.upper():
                orig_colors.append(c)
    # Fallback to colors list
    if not orig_colors and 'colors' in card_dict:
        orig_colors = [c for c in 'WUBRG' if c in [x.upper() for x in card_dict['colors']]]
    # Fallback to color identity list
    if not orig_colors and 'colorIdentity' in card_dict:
        orig_colors = [c for c in 'WUBRG' if c in [x.upper() for x in card_dict['colorIdentity']]]

    orig_colors = sorted(list(set(orig_colors)), key=lambda x: WUBRG.index(x))

    if not orig_colors:
        return card_dict

    # 2. Parse target colors robustly
    target_colors = []
    tokens = re.split(r'[^A-Za-z0-9]', target_colors_str)
    for token in tokens:
        token_upper = token.upper().strip()
        if not token_upper:
            continue
        if token_upper in COLOR_NAME_TO_SYM:
            target_colors.append(COLOR_NAME_TO_SYM[token_upper])
        else:
            for char in token_upper:
                if char in 'WUBRG':
                    target_colors.append(char)

    target_colors = sorted(list(set(target_colors)), key=lambda x: WUBRG.index(x))

    if not target_colors:
        return card_dict

    # 3. Create mapping orig_color -> list of target_colors
    mapping = {}
    if len(orig_colors) >= len(target_colors):
        for i, oc in enumerate(orig_colors):
            mapping[oc] = [target_colors[i % len(target_colors)]]
    else:
        for oc in orig_colors:
            mapping[oc] = []
        for i, tc in enumerate(target_colors):
            oc = orig_colors[i % len(orig_colors)]
            mapping[oc].append(tc)

    # 4. Define simultaneous replacement maps for strings
    word_map = {}
    for oc in orig_colors:
        targets = mapping[oc]
        if not targets:
            continue
        oc_color = COLOR_NAME_MAP[oc]
        tc_colors = [COLOR_NAME_MAP[tc] for tc in targets]
        oc_land = LAND_NAME_MAP[oc]
        tc_lands = [LAND_NAME_MAP[tc] for tc in targets]

        # Color names
        word_map[oc_color] = " and ".join(tc_colors)
        word_map[oc_color.lower()] = " and ".join(c.lower() for c in tc_colors)
        word_map[oc_color.upper()] = " and ".join(c.upper() for c in tc_colors)

        # Land names
        word_map[oc_land] = " and ".join(tc_lands)
        word_map[oc_land.lower()] = " and ".join(l.lower() for l in tc_lands)
        word_map[oc_land.upper()] = " and ".join(l.upper() for l in tc_lands)

    # Helper to replace words
    def replace_words(s):
        if not s or not isinstance(s, str):
            return s
        if not word_map:
            return s
        keys_sorted = sorted(word_map.keys(), key=len, reverse=True)
        pattern = re.compile("|".join(re.escape(k) for k in keys_sorted))
        return pattern.sub(lambda m: word_map[m.group(0)], s)

    # Helper to replace mana symbols
    def replace_mana_symbols(s):
        if not s or not isinstance(s, str):
            return s
        def repl(match):
            interior = match.group(1)
            if interior.upper() in 'WUBRG':
                target_list = mapping.get(interior.upper(), [])
                if not target_list:
                    return match.group(0)
                return "".join(f"{{{tc}}}" for tc in target_list)
            new_interior = []
            for char in interior:
                if char.upper() in 'WUBRG':
                    target_list = mapping.get(char.upper(), [])
                    if target_list:
                        new_char = target_list[0]
                        new_interior.append(new_char if char.isupper() else new_char.lower())
                    else:
                        new_interior.append(char)
                else:
                    new_interior.append(char)
            return "{" + "".join(new_interior) + "}"
        return re.sub(r'\{([^}]+)\}', repl, s)

    # Apply mapping to fields
    if 'name' in card_dict:
        card_dict['name'] = replace_words(card_dict['name'])
    if 'type' in card_dict:
        card_dict['type'] = replace_words(card_dict['type'])
    for field in ['supertypes', 'types', 'subtypes']:
        if field in card_dict and isinstance(card_dict[field], list):
            card_dict[field] = [replace_words(item) for item in card_dict[field]]
    if 'text' in card_dict:
        text = replace_words(card_dict['text'])
        text = replace_mana_symbols(text)
        card_dict['text'] = text
    if 'manaCost' in card_dict:
        card_dict['manaCost'] = replace_mana_symbols(card_dict['manaCost'])
    for field in ['colors', 'colorIdentity']:
        if field in card_dict and isinstance(card_dict[field], list):
            new_list = []
            for item in card_dict[field]:
                if item.upper() in mapping:
                    new_list.extend(mapping[item.upper()])
                else:
                    new_list.append(item)
            card_dict[field] = sorted(list(set(new_list)), key=lambda x: WUBRG.index(x) if x in WUBRG else 99)

    if 'bside' in card_dict:
        card_dict['bside'] = apply_color_shift(card_dict['bside'], target_colors_str)

    return card_dict

def apply_buff_nerf(card_dict, amount):
    if 'power' in card_dict:
        card_dict['power'] = adjust_stat(card_dict['power'], amount)
    if 'toughness' in card_dict:
        card_dict['toughness'] = adjust_stat(card_dict['toughness'], amount)
    if 'pt' in card_dict:
        pt_val = card_dict['pt']
        if '/' in pt_val:
            p, t = pt_val.split('/', 1)
            card_dict['pt'] = f"{adjust_stat(p.strip(), amount)}/{adjust_stat(t.strip(), amount)}"
        else:
            card_dict['pt'] = adjust_stat(pt_val, amount)
    if 'loyalty' in card_dict:
        card_dict['loyalty'] = adjust_stat(card_dict['loyalty'], amount)
    if 'defense' in card_dict:
        card_dict['defense'] = adjust_stat(card_dict['defense'], amount)

    if 'bside' in card_dict:
        card_dict['bside'] = apply_buff_nerf(card_dict['bside'], amount)
    return card_dict

def apply_scale(card_dict, factor, multiply=True):
    if 'power' in card_dict:
        card_dict['power'] = scale_stat(card_dict['power'], factor, multiply)
    if 'toughness' in card_dict:
        card_dict['toughness'] = scale_stat(card_dict['toughness'], factor, multiply)
    if 'pt' in card_dict:
        pt_val = card_dict['pt']
        if '/' in pt_val:
            p, t = pt_val.split('/', 1)
            card_dict['pt'] = f"{scale_stat(p.strip(), factor, multiply)}/{scale_stat(t.strip(), factor, multiply)}"
        else:
            card_dict['pt'] = scale_stat(pt_val, factor, multiply)
    if 'loyalty' in card_dict:
        card_dict['loyalty'] = scale_stat(card_dict['loyalty'], factor, multiply)
    if 'defense' in card_dict:
        card_dict['defense'] = scale_stat(card_dict['defense'], factor, multiply)

    if 'manaCost' in card_dict:
        card_dict['manaCost'] = scale_mana_cost(card_dict['manaCost'], factor, multiply)

    if 'bside' in card_dict:
        card_dict['bside'] = apply_scale(card_dict['bside'], factor, multiply)
    return card_dict

def reforge_card_dict(card_dict, args):
    card_dict = card_dict.copy()
    if args.name: card_dict['name'] = args.name
    if args.cost: card_dict['manaCost'] = args.cost
    if args.type:
        card_dict['type'] = args.type
        # Clear existing split types to allow parse_type_line to re-evaluate
        card_dict.pop('supertypes', None)
        card_dict.pop('types', None)
        card_dict.pop('subtypes', None)

        supertypes, types, subtypes = utils.parse_type_line(args.type)
        if supertypes: card_dict['supertypes'] = supertypes
        if types: card_dict['types'] = types
        if subtypes: card_dict['subtypes'] = subtypes

    if args.text: card_dict['text'] = args.text.replace('\\n', '\n')

    if args.pt:
        if '/' in args.pt:
            p, t = args.pt.split('/', 1)
            card_dict['power'] = p.strip()
            card_dict['toughness'] = t.strip()
        else:
            card_dict['pt'] = args.pt

    if args.loy:
        # Determine if it's a battle or planeswalker
        typeline = card_dict.get('type', '')
        if 'Battle' in typeline:
            card_dict['defense'] = args.loy
        else:
            card_dict['loyalty'] = args.loy

    if args.rarity: card_dict['rarity'] = args.rarity
    if args.set: card_dict['setCode'] = args.set

    # Apply Transformational Modifiers
    if args.color_shift:
        card_dict = apply_color_shift(card_dict, args.color_shift)
    if args.buff is not None:
        card_dict = apply_buff_nerf(card_dict, args.buff)
    if args.nerf is not None:
        card_dict = apply_buff_nerf(card_dict, -args.nerf)
    if args.scale_up is not None:
        card_dict = apply_scale(card_dict, args.scale_up, multiply=True)
    if args.scale_down is not None:
        card_dict = apply_scale(card_dict, args.scale_down, multiply=False)

    return card_dict

def main():
    parser = argparse.ArgumentParser(
        description="Forge a new Magic card or reforge an existing one from the command line, with batch-processing support.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Create a card from scratch and view it
  python3 scripts/mtg_forge.py --name "Jules" --cost "{U}{R}" --type "Legendary Creature" --pt "2/2" --text "T: Draw a card." | python3 decode.py

  # Reforge an existing card (requires data/AllPrintings.json)
  python3 scripts/mtg_forge.py --base "Grizzly Bears" --pt "3/3" --name "Super Bears"

  # Batch-reforge all cards from a file, buffing them by +1/+1
  python3 scripts/mtg_forge.py --infile custom_set.json --buff 1

  # Batch-color-shift all Goblins from MOM to blue and save to a file
  python3 scripts/mtg_forge.py --set MOM --grep "Goblin" --color-shift blue --outfile blue_goblins.json
"""
    )

    # Group: Input / Base
    base_group = parser.add_argument_group('Base Card')
    base_group.add_argument('--base', help='Name of an existing card to use as a template.')
    base_group.add_argument('--infile', default='-',
                            help='Input dataset to search for the base card. Defaults to stdin/AllPrintings.json.')

    # Group: Card Fields
    field_group = parser.add_argument_group('Card Fields')
    field_group.add_argument('-n', '--name', help='Card name.')
    field_group.add_argument('-c', '--cost', help='Mana cost (e.g. "{1}{W}{B}").')
    field_group.add_argument('-t', '--type', help='Full type line (e.g. "Legendary Creature - Human").')
    field_group.add_argument('-x', '--text', help='Rules text (use \\n for newlines).')
    field_group.add_argument('--pt', help='Power/Toughness (e.g. "2/2").')
    field_group.add_argument('--loy', '--loyalty', dest='loy', help='Loyalty or Defense value.')
    field_group.add_argument('-r', '--rarity', help='Rarity (common, uncommon, rare, mythic).')
    field_group.add_argument('--set', help='Set code (e.g. "MOM").')

    # Group: Transformational Modifiers
    trans_group = parser.add_argument_group('Transformational Modifiers')
    trans_group.add_argument('--color-shift', help='Shift card colors to target color or colors (e.g. "U,B" or "blue").')
    trans_group.add_argument('--buff', type=int, nargs='?', const=1, help='Increment power, toughness, loyalty, or defense by an amount.')
    trans_group.add_argument('--nerf', type=int, nargs='?', const=1, help='Decrement power, toughness, loyalty, or defense by an amount.')
    trans_group.add_argument('--scale-up', type=float, nargs='?', const=2.0, help='Scale up stats and generic mana costs proportionally by a factor.')
    trans_group.add_argument('--scale-down', type=float, nargs='?', const=2.0, help='Scale down stats and generic mana costs proportionally by a factor.')

    # Group: Processing Options
    proc_group = parser.add_argument_group('Processing Options')
    proc_group.add_argument('--batch', action='store_true',
                            help='Process and reforge all matching cards in the input instead of a single card.')
    proc_group.add_argument('--limit', type=int, default=0,
                            help='Only process the first N cards.')
    proc_group.add_argument('--shuffle', action='store_true',
                            help='Randomize the order of cards.')
    proc_group.add_argument('--sample', type=int, default=0,
                            help='Pick N random cards (shorthand for --shuffle --limit N).')
    proc_group.add_argument('--sort', choices=['name', 'color', 'identity', 'type', 'cmc', 'rarity', 'power', 'toughness', 'loyalty', 'set', 'pack', 'box', 'complexity', 'score', 'rating', 'power_rating'],
                            help='Sort cards by a specific criterion.')
    proc_group.add_argument('--reverse', action='store_true',
                            help='Reverse the sort order.')

    # Group: Filtering Options
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
    filter_group.add_argument('--colors', action='append',
                        help="Only include cards of specific colors (W, U, B, R, G). Use 'C' or 'A' for colorless. Supports multiple values.")
    filter_group.add_argument('--identity', action='append',
                        help="Only include cards with specific colors in their color identity. Supports multiple values.")
    filter_group.add_argument('--id-count', action='append',
                        help='Only include cards with specific color identity counts. Supports inequalities and ranges.')
    filter_group.add_argument('--cmc', action='append',
                        help='Only include cards with specific CMC values. Supports inequalities and ranges.')
    filter_group.add_argument('--pow', '--power', action='append', dest='pow',
                        help='Only include cards with specific Power values. Supports inequalities and ranges.')
    filter_group.add_argument('--tou', '--toughness', action='append', dest='tou',
                        help='Only include cards with specific Toughness values. Supports inequalities and ranges.')
    filter_group.add_argument('--loy-filter', '--loyalty-filter', '--defense-filter', action='append', dest='loy_filter',
                        help='Only include cards with specific Loyalty or Defense values. Supports inequalities and ranges.')
    filter_group.add_argument('--mechanic', action='append',
                        help='Only include cards with specific mechanical features or keyword abilities. Supports multiple values.')
    filter_group.add_argument('--produces', action='append',
                        help="Only include cards that can produce specific colors of mana (W, U, B, R, G, C, or Any).")
    filter_group.add_argument('--deck-filter', '--decklist-filter', dest='deck',
                        help='Filter cards using a standard MTG decklist file.')
    filter_group.add_argument('--seed', type=int,
                        help='Seed for RNG.')
    filter_group.add_argument('--booster', type=int, default=0,
                        help='Simulate opening N booster packs.')
    filter_group.add_argument('--box', type=int, default=0,
                        help='Simulate opening N booster boxes.')

    # Group: Output Options
    out_group = parser.add_argument_group('Output Options')
    out_group.add_argument('-o', '--outfile', help='Save output to a file instead of printing.')
    out_group.add_argument('--json', action='store_true', help='Output in JSON format (Default).')
    out_group.add_argument('--encoded', action='store_true', help='Output in encoded text format.')
    out_group.add_argument('-S', '--summary', action='store_true', help='Output a one-line summary.')

    # Group: Logging
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')

    args = parser.parse_args()

    # Handle --sample
    if args.sample > 0:
        args.shuffle = True
        args.limit = args.sample

    # Determine input for base card
    infile = args.infile
    if infile == '-' and sys.stdin.isatty():
        default_data = 'data/AllPrintings.json'
        if os.path.exists(default_data):
            infile = default_data

    # Determine if we are running in batch mode
    is_batch_mode = args.batch or (not args.base and not args.name)

    # Initialize output file
    output_f = open(args.outfile, 'w', encoding='utf-8') if args.outfile else sys.stdout

    try:
        if is_batch_mode:
            if args.verbose:
                print(f"Running in batch mode. Loading cards from {infile}...", file=sys.stderr)

            # Re-map set override from args if any to avoid confusion with set filter
            set_filter_val = [args.set] if isinstance(args.set, str) else args.set

            # Resolve set code conflict: args.set is override, set_filter is filter
            # But wait, in command line, if someone specifies --set MOM, do they want to filter by set MOM?
            # Yes! In standard filtering across tools, --set is the filter!
            # If they specify --set, we should use it as a filter when loading cards.
            # But wait! What if they want to override the set on all cards to MOM?
            # In single card mode, --set overrides the set.
            # In batch mode, we can use --set as a filter for loading, but what if they want to override?
            # To be consistent with standard tools, let's treat --set as both:
            # - If they are loading, --set filters the cards by set.
            # - When forging/saving, we can also override if they specify it, or keep it.
            # Wait, if they do `--set MOM --rarity rare`, they probably want to filter by set MOM and rarity rare.
            # So let's pass them to `mtg_open_file`.
            cards = jdecode.mtg_open_file(
                infile, verbose=args.verbose,
                grep=args.grep, vgrep=args.vgrep,
                grep_name=args.grep_name, vgrep_name=args.exclude_name,
                grep_types=args.grep_type, vgrep_types=args.exclude_type,
                grep_text=args.grep_text, vgrep_text=args.exclude_text,
                grep_cost=args.grep_cost, vgrep_cost=args.exclude_cost,
                grep_pt=args.grep_pt, vgrep_pt=args.exclude_pt,
                grep_loyalty=args.grep_loyalty, vgrep_loyalty=args.exclude_loyalty,
                sets=set_filter_val, rarities=args.rarity,
                colors=args.colors, cmcs=args.cmc,
                pows=args.pow, tous=args.tou, loys=args.loy_filter,
                mechanics=args.mechanic,
                produces=args.produces,
                identities=args.identity, id_counts=args.id_count,
                decklist_file=args.deck,
                shuffle=args.shuffle, seed=args.seed,
                booster=args.booster, box=args.box
            )

            if args.sort:
                import sortlib
                cards = sortlib.sort_cards(cards, args.sort, reverse=args.reverse, quiet=True)

            if args.limit > 0:
                cards = cards[:args.limit]

            final_cards = []
            for card in cards:
                card_dict = card.to_dict()
                # Apply overrides/transformational modifiers
                reforged_dict = reforge_card_dict(card_dict, args)
                try:
                    final_card = cardlib.Card(reforged_dict)
                    final_cards.append(final_card)
                except Exception as e:
                    if args.verbose:
                        print(f"Skipping card '{card.name}' due to validation error: {e}", file=sys.stderr)

            # Output results in batch mode
            if args.encoded:
                output_f.write(utils.cardsep.join(c.encode() for c in final_cards) + '\n')
            elif args.summary:
                use_color = sys.stdout.isatty() if not args.outfile else False
                for final_card in final_cards:
                    output_f.write(final_card.summary(ansi_color=use_color) + '\n')
            else:
                # Default: JSON list of card dictionaries
                print(json.dumps([c.to_dict() for c in final_cards], indent=2), file=output_f)

        else:
            # Single card mode (Template or Scratch)
            card_dict = {}

            if args.base:
                if args.verbose:
                    print(f"Searching for base card: {args.base} in {infile}...", file=sys.stderr)

                # Load the base card
                cards = jdecode.mtg_open_file(infile, verbose=args.verbose, grep_name=[f"^{re.escape(args.base)}$"])
                if not cards:
                    # Try fuzzy match if exact fails
                    cards = jdecode.mtg_open_file(infile, verbose=False, grep_name=[re.escape(args.base)])

                if not cards:
                    print(f"Error: Base card '{args.base}' not found.", file=sys.stderr)
                    sys.exit(1)

                # Use the first match
                base_card = cards[0]
                card_dict = base_card.to_dict()
                if args.verbose:
                    print(f"Using '{base_card.name}' as template.", file=sys.stderr)

            # Apply overrides and transformational modifiers
            reforged_dict = reforge_card_dict(card_dict, args)

            # Create a Card object to ensure all internal properties are populated
            # and to support all project output formats.
            try:
                final_card = cardlib.Card(reforged_dict)
            except Exception as e:
                print(f"Error validating forged card: {e}", file=sys.stderr)
                sys.exit(1)

            # Output single card
            if args.encoded:
                output_f.write(final_card.encode() + '\n')
            elif args.summary:
                use_color = sys.stdout.isatty() if not args.outfile else False
                output_f.write(final_card.summary(ansi_color=use_color) + '\n')
            else:
                # Default: JSON
                print(json.dumps(final_card.to_dict(), indent=2), file=output_f)

    finally:
        if args.outfile:
            output_f.close()

if __name__ == "__main__":
    main()
