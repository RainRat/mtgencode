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

COLOR_WORDS = {
    'W': {'name': 'White', 'adj': 'white', 'land': 'Plains', 'land_lower': 'plains', 'land_plural': 'Plains', 'land_plural_lower': 'plains'},
    'U': {'name': 'Blue', 'adj': 'blue', 'land': 'Island', 'land_lower': 'island', 'land_plural': 'Islands', 'land_plural_lower': 'islands'},
    'B': {'name': 'Black', 'adj': 'black', 'land': 'Swamp', 'land_lower': 'swamp', 'land_plural': 'Swamps', 'land_plural_lower': 'swamps'},
    'R': {'name': 'Red', 'adj': 'red', 'land': 'Mountain', 'land_lower': 'mountain', 'land_plural': 'Mountains', 'land_plural_lower': 'mountains'},
    'G': {'name': 'Green', 'adj': 'green', 'land': 'Forest', 'land_lower': 'forest', 'land_plural': 'Forests', 'land_plural_lower': 'forests'},
}

def get_replacement_mappings(src, targets):
    src_words = COLOR_WORDS[src]

    target_names = [COLOR_WORDS[t]['name'] for t in targets]
    target_adjs = [COLOR_WORDS[t]['adj'] for t in targets]
    target_lands = [COLOR_WORDS[t]['land'] for t in targets]
    target_lands_lower = [COLOR_WORDS[t]['land_lower'] for t in targets]
    target_lands_plural = [COLOR_WORDS[t]['land_plural'] for t in targets]
    target_lands_plural_lower = [COLOR_WORDS[t]['land_plural_lower'] for t in targets]

    def join_and(lst):
        if len(lst) == 1: return lst[0]
        return " and ".join(lst)

    def join_or(lst):
        if len(lst) == 1: return lst[0]
        return " or ".join(lst)

    repl_name = join_and(target_names)
    repl_adj = join_and(target_adjs)
    repl_land = join_or(target_lands)
    repl_land_lower = join_or(target_lands_lower)
    repl_land_plural = join_and(target_lands_plural)
    repl_land_plural_lower = join_and(target_lands_plural_lower)

    return [
        (src_words['name'], repl_name),
        (src_words['adj'], repl_adj),
        (src_words['name'].upper(), repl_name.upper()),
        (src_words['adj'].upper(), repl_adj.upper()),
        (src_words['land_plural'], repl_land_plural),
        (src_words['land_plural_lower'], repl_land_plural_lower),
        (src_words['land_plural'].upper(), repl_land_plural.upper()),
        (src_words['land_plural_lower'].upper(), repl_land_plural_lower.upper()),
        (src_words['land'], repl_land),
        (src_words['land_lower'], repl_land_lower),
        (src_words['land'].upper(), repl_land.upper()),
        (src_words['land_lower'].upper(), repl_land_lower.upper()),
    ]

def replace_all(text, rep_dict):
    if not text:
        return text
    pattern = re.compile("|".join(re.escape(k) for k in sorted(rep_dict.keys(), key=len, reverse=True)))
    return pattern.sub(lambda m: rep_dict[m.group(0)], text)

def shift_mana_cost(cost_str, target_colors):
    if not cost_str:
        return cost_str
    pattern = r'\{[WUBRG]\}'
    matches = list(re.finditer(pattern, cost_str, re.IGNORECASE))
    if not matches:
        return cost_str

    new_cost_parts = []
    last_end = 0

    if len(target_colors) <= len(matches):
        for i, match in enumerate(matches):
            new_cost_parts.append(cost_str[last_end:match.start()])
            target_char = target_colors[i] if i < len(target_colors) else target_colors[-1]
            new_cost_parts.append(f"{{{target_char}}}")
            last_end = match.end()
        new_cost_parts.append(cost_str[last_end:])
        return "".join(new_cost_parts)
    else:
        chunk_size = len(target_colors) // len(matches)
        remainder = len(target_colors) % len(matches)

        target_idx = 0
        for i, match in enumerate(matches):
            new_cost_parts.append(cost_str[last_end:match.start()])
            curr_chunk = chunk_size + (1 if i < remainder else 0)
            assigned_colors = target_colors[target_idx : target_idx + curr_chunk]
            target_idx += curr_chunk

            symbol_str = "".join(f"{{{c}}}" for c in assigned_colors)
            new_cost_parts.append(symbol_str)
            last_end = match.end()
        new_cost_parts.append(cost_str[last_end:])
        return "".join(new_cost_parts)

def modify_stat(stat_str, delta, minimum=0):
    if stat_str is None:
        return stat_str
    try:
        val = int(stat_str)
        new_val = max(minimum, val + delta)
        return str(new_val)
    except ValueError:
        match = re.match(r'^(\d+)\+(\*)$', stat_str.strip())
        if match:
            val = int(match.group(1))
            new_val = max(minimum, val + delta)
            return f"{new_val}+{match.group(2)}"
        return stat_str

def scale_mana_cost(cost_str, delta):
    if not cost_str:
        if delta > 0:
            return f"{{{delta}}}"
        return cost_str

    match = re.search(r'\{(\d+)\}', cost_str)
    if match:
        val = int(match.group(1))
        new_val = val + delta
        if new_val > 0:
            return cost_str[:match.start()] + f"{{{new_val}}}" + cost_str[match.end():]
        else:
            return cost_str[:match.start()] + cost_str[match.end():]
    else:
        if delta > 0:
            return f"{{{delta}}}" + cost_str
        return cost_str

def main():
    parser = argparse.ArgumentParser(
        description="Forge a new Magic card or reforge an existing one from the command line.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Create a card from scratch and view it
  python3 scripts/mtg_forge.py --name "Jules" --cost "{U}{R}" --type "Legendary Creature" --pt "2/2" --text "T: Draw a card." | python3 decode.py

  # Reforge an existing card (requires data/AllPrintings.json)
  python3 scripts/mtg_forge.py --base "Grizzly Bears" --pt "3/3" --name "Super Bears"

  # Create a card and save it to a JSON file
  python3 scripts/mtg_forge.py --name "Test" --type "Instant" --cost "{U}" --text "Counter target spell." --outfile card.json
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
    mod_group = parser.add_argument_group('Transformational Modifiers')
    mod_group.add_argument('--color-shift', help='Shift card colors to the target color(s) (e.g. "W", "WU").')
    mod_group.add_argument('--buff', action='store_true', help='Increase Power/Toughness by +1/+1 (or starting loyalty/defense by +1).')
    mod_group.add_argument('--nerf', action='store_true', help='Decrease Power/Toughness by -1/-1 (or starting loyalty/defense by -1).')
    mod_group.add_argument('--scale-up', action='store_true', help='Scale up card cost and stats proportionally.')
    mod_group.add_argument('--scale-down', action='store_true', help='Scale down card cost and stats proportionally.')

    # Group: Output Options
    out_group = parser.add_argument_group('Output Options')
    out_group.add_argument('-o', '--outfile', help='Save output to a file instead of printing.')
    out_group.add_argument('--json', action='store_true', help='Output in JSON format (Default).')
    out_group.add_argument('--encoded', action='store_true', help='Output in encoded text format.')
    out_group.add_argument('-S', '--summary', action='store_true', help='Output a one-line summary.')

    # Group: Logging
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')

    args = parser.parse_args()

    # Determine input for base card
    infile = args.infile
    if infile == '-' and sys.stdin.isatty():
        default_data = 'data/AllPrintings.json'
        if os.path.exists(default_data):
            infile = default_data

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

    # Apply Transformational Modifiers
    if args.color_shift:
        target_colors = [c for c in args.color_shift.upper() if c in 'WUBRG']
        if target_colors:
            source_colors_set = set(re.findall(r'[WUBRG]', card_dict.get('manaCost', ''), re.IGNORECASE))
            source_colors = sorted(list(source_colors_set))
            if not source_colors:
                source_colors = ['G']

            rep_dict = {}
            for src in source_colors:
                mappings = get_replacement_mappings(src, target_colors)
                for old_word, new_word in mappings:
                    rep_dict[old_word] = new_word

            symbol_repl = "".join(f"{{{t}}}" for t in target_colors)
            for src in source_colors:
                rep_dict[f"{{{src}}}"] = symbol_repl
                rep_dict[f"{{{src.lower()}}}"] = symbol_repl.lower()

            if 'name' in card_dict:
                card_dict['name'] = replace_all(card_dict['name'], rep_dict)
            if 'type' in card_dict:
                card_dict['type'] = replace_all(card_dict['type'], rep_dict)
                supertypes, types, subtypes = utils.parse_type_line(card_dict['type'])
                card_dict['supertypes'] = supertypes
                card_dict['types'] = types
                card_dict['subtypes'] = subtypes
            if 'text' in card_dict:
                card_dict['text'] = replace_all(card_dict['text'], rep_dict)

            if utils.json_field_bside in card_dict:
                bside = card_dict[utils.json_field_bside]
                if 'name' in bside: bside['name'] = replace_all(bside['name'], rep_dict)
                if 'type' in bside:
                    bside['type'] = replace_all(bside['type'], rep_dict)
                    supertypes, types, subtypes = utils.parse_type_line(bside['type'])
                    bside['supertypes'] = supertypes
                    bside['types'] = types
                    bside['subtypes'] = subtypes
                if 'text' in bside: bside['text'] = replace_all(bside['text'], rep_dict)
                if 'manaCost' in bside:
                    bside['manaCost'] = shift_mana_cost(bside['manaCost'], target_colors)

            if 'manaCost' in card_dict:
                card_dict['manaCost'] = shift_mana_cost(card_dict['manaCost'], target_colors)

    if args.buff:
        if 'power' in card_dict:
            card_dict['power'] = modify_stat(card_dict['power'], 1, minimum=0)
        if 'toughness' in card_dict:
            card_dict['toughness'] = modify_stat(card_dict['toughness'], 1, minimum=0)
        if 'loyalty' in card_dict:
            card_dict['loyalty'] = modify_stat(card_dict['loyalty'], 1, minimum=1)
        if 'defense' in card_dict:
            card_dict['defense'] = modify_stat(card_dict['defense'], 1, minimum=1)

    if args.nerf:
        if 'power' in card_dict:
            card_dict['power'] = modify_stat(card_dict['power'], -1, minimum=0)
        if 'toughness' in card_dict:
            card_dict['toughness'] = modify_stat(card_dict['toughness'], -1, minimum=0)
        if 'loyalty' in card_dict:
            card_dict['loyalty'] = modify_stat(card_dict['loyalty'], -1, minimum=1)
        if 'defense' in card_dict:
            card_dict['defense'] = modify_stat(card_dict['defense'], -1, minimum=1)

    if args.scale_up:
        if 'power' in card_dict:
            card_dict['power'] = modify_stat(card_dict['power'], 1, minimum=0)
        if 'toughness' in card_dict:
            card_dict['toughness'] = modify_stat(card_dict['toughness'], 1, minimum=0)
        if 'loyalty' in card_dict:
            card_dict['loyalty'] = modify_stat(card_dict['loyalty'], 1, minimum=1)
        if 'defense' in card_dict:
            card_dict['defense'] = modify_stat(card_dict['defense'], 1, minimum=1)
        if 'manaCost' in card_dict:
            card_dict['manaCost'] = scale_mana_cost(card_dict['manaCost'], 1)

    if args.scale_down:
        if 'power' in card_dict:
            card_dict['power'] = modify_stat(card_dict['power'], -1, minimum=0)
        if 'toughness' in card_dict:
            card_dict['toughness'] = modify_stat(card_dict['toughness'], -1, minimum=0)
        if 'loyalty' in card_dict:
            card_dict['loyalty'] = modify_stat(card_dict['loyalty'], -1, minimum=1)
        if 'defense' in card_dict:
            card_dict['defense'] = modify_stat(card_dict['defense'], -1, minimum=1)
        if 'manaCost' in card_dict:
            card_dict['manaCost'] = scale_mana_cost(card_dict['manaCost'], -1)

    # Apply Overrides
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

    # Create a Card object to ensure all internal properties are populated
    # and to support all proyect output formats.
    try:
        # jdecode._normalize_scryfall_card is useful but we built MTGJSON-style
        # Card(card_dict) works best.
        final_card = cardlib.Card(card_dict)
    except Exception as e:
        print(f"Error validating forged card: {e}", file=sys.stderr)
        sys.exit(1)

    # Output
    output_f = open(args.outfile, 'w', encoding='utf-8') if args.outfile else sys.stdout

    try:
        if args.encoded:
            output_f.write(final_card.encode() + '\n')
        elif args.summary:
            # Enable color if output is a TTY
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
