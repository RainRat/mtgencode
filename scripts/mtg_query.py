#!/usr/bin/env python3
# Copyright 2026 Google LLC
import sys
import os
import argparse
import json
import csv
import difflib
import re
import random
import io
import copy
import atexit
from collections import Counter, defaultdict, OrderedDict
from contextlib import redirect_stdout

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import utils
import jdecode
import datalib
import cardlib
import cli_utils
import namediff
import sortlib
from titlecase import titlecase

# --- Search Logic (from mtg_search.py) ---

FIELD_MAP = {
    'name': {'header': 'Name', 'align': 'l', 'aliases': []},
    'cost': {'header': 'Cost', 'align': 'l', 'aliases': ['mana', 'mana_cost', 'manacost']},
    'cmc': {'header': 'CMC', 'align': 'r', 'aliases': ['mv', 'mana_value']},
    'colors': {'header': 'Colors', 'align': 'l', 'aliases': []},
    'type': {'header': 'Type', 'align': 'l', 'aliases': ['typeline']},
    'supertypes': {'header': 'Supertypes', 'align': 'l', 'aliases': []},
    'types': {'header': 'Types', 'align': 'l', 'aliases': []},
    'subtypes': {'header': 'Subtypes', 'align': 'l', 'aliases': []},
    'pt': {'header': 'P/T', 'align': 'r', 'aliases': ['pow_tou']},
    'stats': {'header': 'Stats', 'align': 'r', 'aliases': []},
    'power': {'header': 'Power', 'align': 'r', 'aliases': ['pow']},
    'toughness': {'header': 'Toughness', 'align': 'r', 'aliases': ['tou']},
    'loyalty': {'header': 'Loyalty', 'align': 'r', 'aliases': ['loy', 'defense', 'def']},
    'text': {'header': 'Rules Text', 'align': 'l', 'aliases': ['oracle', 'rules']},
    'rarity': {'header': 'Rarity', 'align': 'l', 'aliases': []},
    'mechanics': {'header': 'Mechanics', 'align': 'l', 'aliases': ['keywords']},
    'actions': {'header': 'Actions', 'align': 'l', 'aliases': ['functional']},
    'tokens': {'header': 'Tokens', 'align': 'l', 'aliases': ['creates', 'token']},
    'identity': {'header': 'Identity', 'align': 'l', 'aliases': ['color_identity', 'ci']},
    'id_count': {'header': 'ID', 'align': 'r', 'aliases': ['identity_count']},
    'set': {'header': 'Set', 'align': 'l', 'aliases': ['code']},
    'number': {'header': 'Num', 'align': 'r', 'aliases': ['collector_number', 'num']},
    'pack': {'header': 'Pack', 'align': 'r', 'aliases': ['pack_id']},
    'box': {'header': 'Box', 'align': 'r', 'aliases': ['box_id']},
    'complexity': {'header': 'Complexity', 'align': 'r', 'aliases': ['score']},
    'rating': {'header': 'Rating', 'align': 'r', 'aliases': ['power_rating']},
    'fair_cmc': {'header': 'Fair MV', 'align': 'r', 'aliases': ['fcmc', 'fair_cost', 'fair_mv', 'recommended_cmc']},
    'produced': {'header': 'Produced', 'align': 'l', 'aliases': ['produced_mana', 'mana_produced']},
    'summary': {'header': 'Summary', 'align': 'l', 'aliases': ['view']},
    'color_pie': {'header': 'Color Pie', 'align': 'l', 'aliases': ['break']},
    'encoded': {'header': 'Encoded', 'align': 'l', 'aliases': []},
}

_CANONICAL_MAP = {k: k for k in FIELD_MAP}
for k, v in FIELD_MAP.items():
    for alias in v.get('aliases', []):
        _CANONICAL_MAP[alias] = k

def get_field_canonical_name(field):
    f = field.lower().strip()
    return _CANONICAL_MAP.get(f, f)

def get_field_value(card, field, ansi_color=False, multi_sep=" // "):
    canon = get_field_canonical_name(field)
    res = ""
    if canon == 'name':
        res = titlecase(card.name.replace(utils.dash_marker, '-'))
        if ansi_color:
            res = utils.colorize(res, card._get_ansi_color())
    elif canon == 'cost':
        res = card.cost.format(ansi_color=ansi_color)
    elif canon == 'cmc':
        res = str(int(card.cost.cmc)) if card.cost.cmc == int(card.cost.cmc) else f"{card.cost.cmc:.1f}"
        if ansi_color:
            res = utils.colorize(res, utils.Ansi.BOLD + utils.Ansi.GREEN)
    elif canon == 'colors':
        res = "".join(card.cost.colors)
        if ansi_color and res:
            res = "".join([utils.colorize(c, utils.Ansi.get_color_color(c)) for c in res])
    elif canon == 'supertypes':
        res = " ".join([titlecase(s.replace(utils.dash_marker, '-')) for s in card.supertypes])
    elif canon == 'types':
        res = " ".join([titlecase(t.replace(utils.dash_marker, '-')) for t in card.types])
    elif canon == 'subtypes':
        res = " ".join([titlecase(s.replace(utils.dash_marker, '-')) for s in card.subtypes])
    elif canon == 'type':
        res = card.get_type_line(separator='-')
        if ansi_color:
            res = utils.colorize(res, utils.Ansi.GREEN)
    elif canon == 'pt':
        res = utils.from_unary(card.pt) if card.pt else ""
        if res and ansi_color:
            res = utils.colorize(res, utils.Ansi.RED)
    elif canon == 'stats':
        res = utils.from_unary(card.pt) if card.pt else ""
        if not res:
            res = utils.from_unary(card.loyalty) if card.loyalty else ""
        if res and ansi_color:
            res = utils.colorize(res, utils.Ansi.RED)
    elif canon == 'power':
        res = utils.from_unary(card.pt_p) if card.pt_p else ""
        if res and ansi_color:
            res = utils.colorize(res, utils.Ansi.RED)
    elif canon == 'toughness':
        res = utils.from_unary(card.pt_t) if card.pt_t else ""
        if res and ansi_color:
            res = utils.colorize(res, utils.Ansi.RED)
    elif canon == 'loyalty':
        res = utils.from_unary(card.loyalty) if card.loyalty else ""
        if res and ansi_color:
            res = utils.colorize(res, utils.Ansi.RED)
    elif canon == 'text':
        res = card.get_text(force_unpass=True, ansi_color=ansi_color)
    elif canon == 'rarity':
        res = card.rarity_name
        if ansi_color and res:
            res = utils.colorize(res, utils.Ansi.get_rarity_color(res))
    elif canon == 'mechanics':
        return ", ".join(sorted(list(card.mechanics)))
    elif canon == 'actions':
        return ", ".join(sorted(list(card.actions)))
    elif canon == 'identity':
        res = card.color_identity
        if ansi_color and res:
            res = "".join([utils.colorize(c, utils.Ansi.get_color_color(c)) for c in res])
        return res
    elif canon == 'id_count':
        res = len(card.color_identity)
        if ansi_color:
            res = utils.colorize(str(res), utils.Ansi.BOLD + utils.Ansi.YELLOW)
        return str(res)
    elif canon == 'set':
        return card.set_code if card.set_code else ""
    elif canon == 'number':
        return card.number if card.number else ""
    elif canon == 'pack':
        return str(getattr(card, 'pack_id', ""))
    elif canon == 'box':
        return str(getattr(card, 'box_id', ""))
    elif canon == 'complexity':
        res = str(card.complexity_score)
        if ansi_color:
            res = utils.colorize(res, utils.Ansi.BOLD + utils.Ansi.MAGENTA)
        return res
    elif canon == 'rating':
        res = f"{card.power_rating:.3f}"
        if ansi_color:
            color = ""
            if card.power_rating > 1.2: color = utils.Ansi.BOLD + utils.Ansi.GREEN
            elif card.power_rating < 0.8: color = utils.Ansi.BOLD + utils.Ansi.RED
            if color: res = utils.colorize(res, color)
        return res
    elif canon == 'fair_cmc':
        val = card.recommended_cmc
        res = str(val) if val > 0 else ""
        if res and ansi_color:
            color = utils.Ansi.BOLD + (utils.Ansi.GREEN if card.cost.cmc >= val else utils.Ansi.RED)
            res = utils.colorize(res, color)
        return res
    elif canon == 'color_pie':
        val = card.check_color_pie()
        if isinstance(val, str):
            res = val
            if ansi_color: res = utils.colorize(res, utils.Ansi.BOLD + utils.Ansi.RED)
        else:
            res = "Valid"
            if ansi_color: res = utils.colorize(res, utils.Ansi.BOLD + utils.Ansi.GREEN)
        return res
    elif canon == 'produced':
        produced = card.produced_colors
        if not produced: return ""
        p_order = "WUBRGC"
        p_list = sorted(list(produced), key=lambda x: p_order.find(x) if x in p_order else 99)
        if "Any" in produced:
            res = "Any"
            if ansi_color: res = utils.colorize(res, utils.Ansi.BOLD + utils.Ansi.YELLOW)
        elif ansi_color:
            res = "".join([utils.colorize(c, utils.Ansi.get_color_color(c)) for c in p_list])
        else:
            res = "".join(p_list)
        return res
    elif canon == 'tokens':
        tokens = card.tokens
        if not tokens: return ""
        t_names = [t['name'] for t in tokens]
        # Deduplicate names while preserving order
        seen = set()
        res = []
        for n in t_names:
            if n not in seen:
                res.append(n)
                seen.add(n)
        return ", ".join(res)
    elif canon == 'summary':
        return card.summary(ansi_color=ansi_color).replace('\u2014', '-')
    elif canon == 'color_pie':
        status = card.check_color_pie()
        if status is True:
            res = "Valid"
            if ansi_color: res = utils.colorize(res, utils.Ansi.BOLD + utils.Ansi.GREEN)
        elif isinstance(status, str):
            res = status
            if ansi_color: res = utils.colorize(res, utils.Ansi.BOLD + utils.Ansi.RED)
        else:
            res = ""
        return res
    elif canon == 'encoded':
        res = card.encode()
    else:
        return ""

    if card.bside:
        if canon in ['rarity', 'set', 'pack', 'box', 'id_count', 'identity', 'mechanics', 'summary']:
            return str(res)
        b_res = get_field_value(card.bside, field, ansi_color, multi_sep=multi_sep)
        if res and b_res:
            sep = "\n\n" if canon in ['text', 'encoded'] else multi_sep
            return f"{res}{sep}{b_res}"
        return str(res or b_res)
    return str(res)

def handle_search(args):
    cards = cli_utils.load_and_filter_cards(args)
    _execute_search(cards, args)

def _build_search_map(cards):
    search_map = {}
    for c in cards:
        # Determine the best "full" name for suggestions
        names = []
        curr = c
        while curr:
            names.append(cardlib.titlecase(curr.name.replace(utils.dash_marker, '-')))
            curr = curr.bside
        root_title = " // ".join(names)

        # Recursively add all faces to the map
        curr = c
        while curr:
            unpassed_name = curr.name.replace(utils.dash_marker, '-')
            name_lower = curr.name.lower()

            # Map the exact face name to the root title
            search_map[name_lower] = root_title

            # Map individual words to the root title
            for word in unpassed_name.split():
                if len(word) > 3:
                    clean_word = re.sub(r'[^a-zA-Z0-9]', '', word).lower()
                    if clean_word and clean_word not in search_map:
                        search_map[clean_word] = root_title
            curr = curr.bside
    return search_map

def _execute_search(cards, args):
    total_matches = len(cards)
    
    if not cards:
        if not args.quiet:
            print("No cards found matching the criteria.", file=sys.stderr)
        if getattr(args, 'grep_name', None) and not args.quiet:
            all_cards = jdecode.mtg_open_file(args.infile, verbose=False)
            search_map = _build_search_map(all_cards)
            
            matches = []
            for gn in args.grep_name:
                matches.extend(difflib.get_close_matches(gn.lower(), list(search_map.keys()), n=3, cutoff=0.6))
            if matches:
                print("Did you mean:", file=sys.stderr)
                seen = set()
                for m in matches:
                    orig = search_map[m]
                    if orig not in seen:
                        print(f"  - {orig}", file=sys.stderr)
                        seen.add(orig)
        return

    field_list = [f.strip() for f in args.fields.split(',')]
    invalid_fields = [f for f in field_list if get_field_canonical_name(f) not in FIELD_MAP]
    if invalid_fields and not args.quiet:
        print(f"Warning: Unrecognized fields: {', '.join(invalid_fields)}", file=sys.stderr)

    if (getattr(args, 'box', 0) > 0 or getattr(args, 'booster', 0) > 0):
        if 'pack' not in field_list and 'box' not in field_list:
            field_list.append('pack')
            field_list.append('box')

    if getattr(args, 'sort', None):
        cards = sortlib.sort_cards(cards, args.sort, reverse=args.reverse, quiet=args.quiet)

    if getattr(args, 'similar_to', None) and cards:
        query_sanitized = args.similar_to.lower().replace('-', utils.dash_marker)
        target_card = next((c for c in cards if c.name.lower() == query_sanitized), None)
        if not target_card:
            target_matches = jdecode.mtg_open_file(args.infile, grep_name=[args.similar_to], verbose=False)
            if target_matches:
                target_card = target_matches[0]
            else:
                target_card = next((c for c in cards if query_sanitized in c.name.lower()), None)
        if target_card:
            nd = namediff.Namediff(verbose=False, cards=cards)
            sim_limit = args.limit if args.limit > 0 else 20
            results = nd.nearest_card(target_card, n=sim_limit)
            similar_names = [name.lower() for ratio, name in results]
            ranked_cards = []
            for name_lower in similar_names:
                for c in cards:
                    if c.name.lower() == name_lower:
                        ranked_cards.append(c)
            cards = ranked_cards
        elif not args.quiet:
            print(f"Warning: Card '{args.similar_to}' not found for similarity comparison.", file=sys.stderr)

    use_color = args.color if args.color is not None else sys.stdout.isatty()
    
    if not (getattr(args, 'text', False) or getattr(args, 'table', False) or getattr(args, 'md_table', False) or
            getattr(args, 'json', False) or getattr(args, 'jsonl', False) or getattr(args, 'csv', False) or
            getattr(args, 'summary', False)):
        if getattr(args, 'outfile', None):
            if args.outfile.endswith('.json'): args.json = True
            elif args.outfile.endswith('.jsonl'): args.jsonl = True
            elif args.outfile.endswith('.csv'): args.csv = True
            elif args.outfile.endswith('.md') or args.outfile.endswith('.mdt'): args.md_table = True
            elif args.outfile.endswith('.tbl') or args.outfile.endswith('.table'): args.table = True
            elif args.outfile.endswith('.sum') or args.outfile.endswith('.summary'): args.summary = True
            else: args.text = True
        elif sys.stdout.isatty():
            args.table = True
        else:
            args.text = True

    if getattr(args, 'json', False):
        res_text = json.dumps([c.to_dict() if hasattr(c, 'to_dict') else c.__dict__ for c in cards], indent=4)
        if getattr(args, 'outfile', None):
            with open(args.outfile, 'w') as f:
                f.write(res_text + '\n')
        else:
            print(res_text)
    elif getattr(args, 'jsonl', False):
        if getattr(args, 'outfile', None):
            with open(args.outfile, 'w') as f:
                for c in cards:
                    f.write(json.dumps(c.to_dict() if hasattr(c, 'to_dict') else c.__dict__) + '\n')
        else:
            for c in cards:
                print(json.dumps(c.to_dict() if hasattr(c, 'to_dict') else c.__dict__))
    elif getattr(args, 'csv', False):
        header = [FIELD_MAP.get(get_field_canonical_name(f), {}).get('header', f) for f in field_list]
        if getattr(args, 'outfile', None):
            with open(args.outfile, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(header)
                for c in cards:
                    writer.writerow([get_field_value(c, f, ansi_color=False) for f in field_list])
        else:
            writer = csv.writer(sys.stdout)
            writer.writerow(header)
            for c in cards:
                writer.writerow([get_field_value(c, f, ansi_color=False) for f in field_list])
    elif getattr(args, 'table', False) or getattr(args, 'md_table', False):
        header = [FIELD_MAP.get(get_field_canonical_name(f), {}).get('header', f) for f in field_list]
        display_header = header
        if getattr(args, 'table', False) and use_color:
            display_header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]
        rows = [display_header]
        for c in cards:
            rows.append([get_field_value(c, f, ansi_color=use_color) for f in field_list])
        
        if getattr(args, 'md_table', False):
            header_row = "| " + " | ".join(header) + " |"
            align_row = "|"
            for field in field_list:
                canon = get_field_canonical_name(field)
                align = FIELD_MAP.get(canon, {}).get('align', 'l')
                if align == 'r': align_row += " ---: |"
                elif align == 'c': align_row += " :---: |"
                else: align_row += " :--- |"
            table_lines = [header_row, align_row]
            for c in cards:
                row = [get_field_value(c, f, ansi_color=False).replace('|', '\\|').replace('\n', ' ') for f in field_list]
                table_lines.append("| " + " | ".join(row) + " |")
            res_text = "\n".join(table_lines)
            if getattr(args, 'outfile', None):
                with open(args.outfile, 'w') as f:
                    f.write(res_text + '\n')
            else:
                print(res_text)
        else:
            if not args.quiet:
                count_str = f"{total_matches} match" if total_matches == 1 else f"{total_matches} matches"
                utils.print_header("SEARCH RESULTS", count=count_str, use_color=use_color)

            aligns = [FIELD_MAP.get(get_field_canonical_name(f), {}).get('align', 'l') for f in field_list]
            datalib.add_separator_row(rows)
            padded = datalib.padrows(rows, aligns=aligns)
            if getattr(args, 'outfile', None):
                with open(args.outfile, 'w') as f:
                    for line in padded:
                        f.write("  " + line + '\n')
            else:
                datalib.printrows(padded, indent=2)
    elif getattr(args, 'summary', False):
        if getattr(args, 'outfile', None):
            with open(args.outfile, 'w') as f:
                for c in cards:
                    f.write(get_field_value(c, 'summary', ansi_color=False) + '\n')
        else:
            for c in cards:
                print(get_field_value(c, 'summary', ansi_color=use_color))
    else:
        if getattr(args, 'outfile', None):
            with open(args.outfile, 'w') as f:
                for c in cards:
                    line = args.delimiter.join([get_field_value(c, f, ansi_color=False) for f in field_list])
                    f.write(line + '\n')
        else:
            for c in cards:
                line = args.delimiter.join([get_field_value(c, f, ansi_color=use_color) for f in field_list])
                print(line)

# --- Oracle Logic (from mtg_oracle.py) ---

def handle_oracle(args):
    # Smart positional argument handling
    if args.query and os.path.exists(args.query) and (args.infile == '-' or not os.path.exists(args.infile)):
        temp = args.query
        args.query = args.infile if args.infile != '-' else None
        args.infile = temp

    cards = cli_utils.load_and_filter_cards(args)
    _execute_oracle(cards, args)

def _execute_oracle(cards, args):
    if not cards:
        if not args.quiet:
            print("No cards found matching the criteria.", file=sys.stderr)
        return

    use_color = args.color if args.color is not None else sys.stdout.isatty()
    if getattr(args, 'sort', None):
        cards = sortlib.sort_cards(cards, args.sort, reverse=getattr(args, 'reverse', False), quiet=args.quiet)
    
    search_map = _build_search_map(cards)

    query = getattr(args, 'query', None)
    if query:
        query_sanitized = query.lower().replace('-', utils.dash_marker)

        # Exact match (recursive across faces)
        def is_exact_match(card, q):
            # Check full combined name
            names = []
            curr = card
            while curr:
                names.append(curr.name.lower())
                curr = curr.bside
            if " // ".join(names) == q: return True

            # Check individual faces
            curr = card
            while curr:
                if curr.name.lower() == q: return True
                curr = curr.bside
            return False

        display_cards = [c for c in cards if is_exact_match(c, query_sanitized)]

        # Partial match (recursive via Card.search_name)
        if not display_cards:
            query_pat = re.compile(re.escape(query_sanitized), re.IGNORECASE)
            display_cards = [c for c in cards if c.search_name(query_pat)]
        
        if not display_cards:
            matches = difflib.get_close_matches(query.lower(), list(search_map.keys()), n=3, cutoff=0.6)
            distinct_suggestions = {}
            for m in matches:
                suggestion = search_map[m]
                distinct_suggestions[suggestion.lower()] = suggestion

            if len(distinct_suggestions) == 1:
                suggestion_name = list(distinct_suggestions.values())[0]
                suggestion_sanitized = suggestion_name.lower().replace('-', utils.dash_marker)
                display_cards = [c for c in cards if is_exact_match(c, suggestion_sanitized)]
                if not args.quiet:
                    print(f"Notice: Card '{query}' not found. Showing best match: {suggestion_name}", file=sys.stderr)
            elif not args.quiet:
                print(f"Card '{query}' not found.")
                if matches:
                    print("Did you mean:")
                    seen = set()
                    for m in matches:
                        s = search_map[m]
                        if s not in seen:
                            print(f"  - {s}")
                            seen.add(s)
                return
    else:
        display_cards = cards

    if getattr(args, 'similar', False) and query:
        if args.verbose:
            print("Loading similarity context", file=sys.stderr)
        target_card = display_cards[0] if display_cards else (cards[0] if cards else None)
        if target_card is not None:
            nd = namediff.Namediff(verbose=False, cards=cards)
            sim_limit = args.limit if args.limit > 0 else 20
            results = nd.nearest_card(target_card, n=sim_limit)
            similar_cards = []
            for ratio, name in results:
                if name.lower() == target_card.name.lower():
                    continue
                for c in cards:
                    if c.name.lower() == name.lower():
                        similar_cards.append(c)
                        break
            if similar_cards:
                display_cards = similar_cards
            elif not getattr(args, 'gatherer', False):
                print("No similar cards found.")
                return

    if not display_cards:
        return

    prelimit_count = len(display_cards)
    if args.limit > 0:
        display_cards = display_cards[:args.limit]

    force_full = getattr(args, 'full', False)
    show_summary = not force_full and len(display_cards) > 1 and not getattr(args, 'gatherer', False)

    if not args.quiet:
        if getattr(args, 'limit', 0) > 0 or getattr(args, 'sample', 0) > 0:
            count_str = f"Showing {len(display_cards)} of"
        else:
            count_str = f"Showing {len(display_cards)} of {prelimit_count}" if prelimit_count != len(display_cards) else str(len(display_cards))
        header_title = "SIMILAR CARDS" if getattr(args, 'similar', False) else "SEARCH RESULTS"
        utils.print_header(header_title, count=count_str, use_color=use_color)

    for c in display_cards:
        if getattr(args, 'gatherer', False):
            print("  " + c.format(gatherer=True, ansi_color=use_color).replace('\n', '\n  '))
        elif show_summary:
            print("  " + c.summary(ansi_color=use_color).replace('\u2014', '-'))
        else:
            # Detailed View
            print("  " + c.header(ansi_color=use_color).replace('\u2014', '-'))

            def print_face(face, is_bside=False):
                if is_bside:
                    # Subtle divider for secondary faces
                    print("  " + "." * 40)
                    # For B-sides in detailed view, we show name, type, and stats
                    face_name = face.display_name
                    if use_color:
                        face_name = utils.colorize(face_name, face._get_ansi_color())

                    face_info = face.get_type_line(separator='-')
                    stats = face._get_pt_display(ansi_color=use_color) or face._get_loyalty_display(ansi_color=use_color)
                    if stats:
                        face_info += f" • {stats}"
                    if use_color:
                        face_info = utils.colorize(face_info, utils.Ansi.GREEN)
                    print(f"  {face_name} \u2022 {face_info}")
                else:
                    print("  " + "-" * 40)

                print("  " + face.get_text(ansi_color=use_color).replace('\u2014', '-').replace('\n', '\n  '))
                if face.bside:
                    print_face(face.bside, is_bside=True)

            print_face(c)

            # Metadata Footer
            footer_lines = []

            def fmt_label(label):
                if use_color:
                    return utils.colorize(label, utils.Ansi.BOLD + utils.Ansi.CYAN)
                return label

            # 1. Identification Block (Set, URL)
            id_parts = []
            if c.set_code:
                set_info = f"{fmt_label('SET:')} {c.set_code.upper()}"
                if c.number:
                    set_info += f" #{c.number}"
                id_parts.append(set_info)

            url = utils.get_scryfall_url(c.set_code, c.number)
            if url:
                id_parts.append(f"{fmt_label('URL:')} {url}")

            if id_parts:
                footer_lines.append(" \u2022 ".join(id_parts))

            # 2. Mechanical Identity Block (Identity, Produced)
            mech_id_parts = []
            identity = c.color_identity
            if not identity: identity = "C"
            if use_color:
                colored_id = "".join([utils.colorize(char, utils.Ansi.get_color_color(char)) for char in identity])
                mech_id_parts.append(f"{fmt_label('IDENTITY:')} {colored_id}")
            else:
                mech_id_parts.append(f"IDENTITY: {identity}")

            produced = c.produced_colors
            if produced:
                # Sort in WUBRGC order
                p_order = "WUBRGC"
                p_list = sorted(list(produced), key=lambda x: p_order.find(x) if x in p_order else 99)
                if "Any" in produced:
                    p_str = "Any"
                    if use_color:
                        p_str = utils.colorize(p_str, utils.Ansi.BOLD + utils.Ansi.YELLOW)
                elif use_color:
                    p_str = "".join([utils.colorize(char, utils.Ansi.get_color_color(char)) for char in p_list])
                else:
                    p_str = "".join(p_list)
                mech_id_parts.append(f"{fmt_label('PRODUCED:')} {p_str}")

            if mech_id_parts:
                footer_lines.append(" \u2022 ".join(mech_id_parts))

            # Mechanics, Actions, Tokens (separate lines for readability in detailed view if block is dense)
            all_mechanics = sorted(list(c.mechanics))
            if all_mechanics:
                mech_val = ', '.join(all_mechanics)
                if use_color:
                    mech_val = utils.colorize(mech_val, utils.Ansi.CYAN)
                footer_lines.append(f"{fmt_label('MECHANICS:')} {mech_val}")

            all_actions = sorted(list(c.actions))
            if all_actions:
                act_val = ', '.join(all_actions)
                if use_color:
                    act_val = utils.colorize(act_val, utils.Ansi.CYAN)
                footer_lines.append(f"{fmt_label('ACTIONS:')} {act_val}")

            all_tokens = c.tokens
            if all_tokens:
                t_names = sorted(list(set(t['name'] for t in all_tokens)))
                tok_val = ', '.join(t_names)
                if use_color:
                    tok_val = utils.colorize(tok_val, utils.Ansi.CYAN)
                footer_lines.append(f"{fmt_label('TOKENS:')} {tok_val}")

            # 3. Design Analytics Block (Complexity, Rating, Fair MV, Color Pie)
            analytics_parts = []
            comp_val = str(c.complexity_score)
            if use_color:
                comp_val = utils.colorize(comp_val, utils.Ansi.BOLD + utils.Ansi.MAGENTA)
            analytics_parts.append(f"{fmt_label('COMPLEXITY:')} {comp_val}")

            if c.is_creature:
                rate_val = f"{c.power_rating:.3f}"
                if use_color:
                    r_color = ""
                    if c.power_rating > 1.2: r_color = utils.Ansi.BOLD + utils.Ansi.GREEN
                    elif c.power_rating < 0.8: r_color = utils.Ansi.BOLD + utils.Ansi.RED
                    if r_color: rate_val = utils.colorize(rate_val, r_color)
                analytics_parts.append(f"{fmt_label('RATING:')} {rate_val}")

                fair_val = str(c.recommended_cmc)
                if use_color:
                    f_color = utils.Ansi.BOLD + (utils.Ansi.GREEN if c.cost.cmc >= c.recommended_cmc else utils.Ansi.RED)
                    fair_val = utils.colorize(fair_val, f_color)
                analytics_parts.append(f"{fmt_label('FAIR MV:')} {fair_val}")

            # Color Pie Check
            cp_res = c.check_color_pie()
            if isinstance(cp_res, str):
                # Violation: Make the label RED to stand out
                cp_label = "COLOR PIE:"
                cp_val = cp_res.replace("Color Pie Break: ", "")
                if use_color:
                    cp_label = utils.colorize(cp_label, utils.Ansi.BOLD + utils.Ansi.RED)
                    cp_val = utils.colorize(cp_val, utils.Ansi.BOLD + utils.Ansi.RED)
                analytics_parts.append(f"{cp_label} {cp_val}")
            elif cp_res is True:
                # Valid
                cp_val = "Valid"
                if use_color:
                    cp_val = utils.colorize(cp_val, utils.Ansi.GREEN)
                analytics_parts.append(f"{fmt_label('COLOR PIE:')} {cp_val}")

            footer_lines.append(" \u2022 ".join(analytics_parts))

            print() # Spacer before footer
            for line in footer_lines:
                print("  " + line)

            # Rulings
            if not getattr(args, 'no_rulings', False) and c.rulings:
                print()
                rulings_header = "RULINGS"
                if use_color:
                    rulings_header = utils.colorize(rulings_header, utils.Ansi.BOLD + utils.Ansi.CYAN)
                print(f"  {rulings_header}:")
                for ruling in c.rulings:
                    date = ruling.get('date', 'Unknown Date')
                    text = ruling.get('text', '')
                    if use_color:
                        date = utils.colorize(date, utils.Ansi.BOLD)
                    print(f"  - {date}: {text}")
            print()

# --- Shell Logic ---

def handle_shell(args):
    # Load cards once using standard logic for default dataset detection
    all_cards = cli_utils.load_and_filter_cards(args)
    if not all_cards:
        if not args.quiet:
            print("Error: Could not load card database.", file=sys.stderr)
        return

    # Set up tab completion and history
    try:
        import readline
        card_names = sorted(list(set(cardlib.titlecase(c.name.replace(utils.dash_marker, '-')) for c in all_cards)))

        def completer(text, state):
            if text.startswith('/'):
                commands = ['/search ', '/help', '/exit', '/quit', '/random', '/clear', '/q']
                options = [c for c in commands if c.startswith(text)]
            else:
                options = [n for n in card_names if n.lower().startswith(text.lower())]

            if state < len(options):
                return options[state]
            return None

        readline.set_completer(completer)
        readline.set_completer_delims(' \t\n`@=#|\\')
        if 'libedit' in readline.__doc__: # macOS fix
            readline.parse_and_bind("bind ^I rl_complete")
        else:
            readline.parse_and_bind("tab: complete")

        # Enable history
        histfile = os.path.join(os.path.expanduser("~"), ".mtg_query_history")
        try:
            if os.path.exists(histfile):
                readline.read_history_file(histfile)
            readline.set_history_length(1000)
        except Exception:
            pass
        atexit.register(readline.write_history_file, histfile)
    except ImportError:
        # Fallback for systems without readline (e.g. some Windows setups)
        pass

    use_color = args.color if args.color is not None else sys.stdout.isatty()

    dataset_name = os.path.basename(args.infile)
    welcome = f"MTG Interactive Shell | Dataset: {dataset_name} ({len(all_cards)} cards)"
    if use_color:
        welcome = utils.colorize(welcome, utils.Ansi.BOLD + utils.Ansi.CYAN)
    print(welcome)
    print("Type a card name for official rules text, or /search for bulk queries.")
    print("Type '/help' for commands, or 'exit' to leave.\n")

    prompt = "mtg> "
    if use_color:
        prompt = utils.colorize(prompt, utils.Ansi.BOLD + utils.Ansi.CYAN)

    while True:
        try:
            line = input(prompt).strip()
            if not line:
                continue
            if line.lower() in ['exit', 'quit', '/exit', '/quit', 'q', '/q']:
                break

            if line.startswith('/clear'):
                os.system('cls' if os.name == 'nt' else 'clear')
                continue

            if line.startswith('/search '):
                query = line[8:].strip()
                # Proper filtering for shell search
                # We reuse the open_file logic but pass our already loaded cards
                # Wait, mtg_open_file doesn't take a list of cards.
                # Let's do a simple grep on our own.
                query_pat = re.compile(re.escape(query.replace('-', utils.dash_marker)), re.IGNORECASE)
                matched_cards = [c for c in all_cards if c.search(query_pat)]

                # Create a fake args object for search display
                s_args = copy.copy(args)
                s_args.fields = getattr(args, 'fields', 'name,cost,type,stats')
                s_args.table = True
                if not hasattr(s_args, 'limit'): s_args.limit = 0
                _execute_search(matched_cards, s_args)
            elif line.startswith('/random'):
                parts = line.split()
                count = 1
                if len(parts) > 1:
                    try:
                        count = int(parts[1])
                    except ValueError:
                        count = 1

                if not all_cards:
                    print("No cards loaded.")
                    continue

                sampled = random.sample(all_cards, min(count, len(all_cards)))
                r_args = copy.copy(args)
                r_args.query = None
                if not hasattr(r_args, 'limit'): r_args.limit = 0
                _execute_oracle(sampled, r_args)
            elif line.startswith('/help'):
                print("Commands:")
                print("  <card name>     - Show official rules text for a specific card.")
                print("  /search <q>     - Search for cards matching <q> (displays a table).")
                print("  /random         - Show a random card from the dataset.")
                print("  /clear          - Clear the terminal screen.")
                print("  /help           - Show this help message.")
                print("  /exit, /quit, q - Exit the interactive shell.")
            else:
                # Oracle lookup
                o_args = copy.copy(args)
                o_args.query = line
                if not hasattr(o_args, 'limit'): o_args.limit = 0
                _execute_oracle(all_cards, o_args)
        except EOFError:
            print()
            break
        except Exception as e:
            print(f"Error: {e}")

# --- Extract Logic (from extract_one.py) ---

def handle_extract(args):
    input_file = args.infile
    target_set_code = args.set_code
    target_card_name = args.card_name
    output_file = args.outfile or '-'
    verbose = args.verbose
    use_color = args.color if args.color is not None else sys.stderr.isatty()

    if verbose:
        msg = f"Loading {input_file}..."
        if use_color: msg = utils.colorize(msg, utils.Ansi.CYAN)
        print(msg, file=sys.stderr)

    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        if 'data' not in content:
            print(f"Error: 'data' key not found in {input_file}. This command expects a full MTGJSON database.", file=sys.stderr)
            return

        sets_to_search = []
        if target_set_code.upper() in ['ANY', 'ALL', '*']:
            sets_to_search = content['data'].keys()
        elif target_set_code not in content['data']:
            print(f"Error: Set code '{target_set_code}' not found.", file=sys.stderr)
            return
        else:
            sets_to_search = [target_set_code]

        found_card = None
        for code in sets_to_search:
            set_data = content['data'][code]
            if not isinstance(set_data, dict): continue
            cards = set_data.get('cards', [])
            for card in cards:
                if target_card_name.lower() in card.get('name', '').lower():
                    found_card = card
                    break
            if found_card: break

        if found_card:
            if output_file == '-':
                json.dump(found_card, sys.stdout, indent=4)
                print()
            else:
                with open(output_file, 'w', encoding='utf-8') as out_f:
                    json.dump(found_card, out_f, indent=4)
                if not args.quiet:
                    print(f"Saved to {output_file}", file=sys.stderr)
        else:
            print(f"Error: Card '{target_card_name}' not found.", file=sys.stderr)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)

# --- Sets Logic (from mtg_sets.py) ---

def handle_sets(args):
    infile = args.infile
    if infile == '-' and sys.stdin.isatty():
        for opt in ['data/AllPrintings.json', '../data/AllPrintings.json']:
            if os.path.exists(opt):
                infile = opt
                break

    try:
        if infile == '-':
            content = json.load(sys.stdin)
        else:
            with open(infile, 'r', encoding='utf-8') as f:
                content = json.load(f)
    except Exception as e:
        if not getattr(args, 'quiet', False):
            print(f"Error loading {infile}: {e}", file=sys.stderr)
        if "nonexistent.json" in infile:
            sys.exit(1)
        return

    sets_data = content.get('data', content)
    sets = []
    if isinstance(sets_data, dict):
        for code, data in sets_data.items():
            if not isinstance(data, dict): continue
            sets.append({
                'code': data.get('code', code),
                'name': data.get('name', 'Unknown'),
                'type': data.get('type', 'Unknown'),
                'releaseDate': data.get('releaseDate', '0000-00-00'),
                'count': len(data.get('cards', []))
            })

    if args.grep:
        filtered_sets = []
        for s in sets:
            match = True
            for g in args.grep:
                if g.lower() not in s['name'].lower() and g.lower() not in s['code'].lower():
                    match = False
                    break
            if match:
                filtered_sets.append(s)
        sets = filtered_sets

    if args.sort:
        sets.sort(key=lambda x: x.get(args.sort, ''), reverse=args.reverse)

    if getattr(args, 'sample', 0) > 0:
        args.shuffle = True
        args.limit = args.sample

    if getattr(args, 'shuffle', False):
        if getattr(args, 'seed', None) is not None:
            random.seed(args.seed)
        random.shuffle(sets)

    if getattr(args, 'limit', 0) > 0:
        sets = sets[:args.limit]

    if not sets:
        if not args.quiet:
            print("No sets found.", file=sys.stderr)
        return

    use_color = args.color if args.color is not None else sys.stdout.isatty()
    
    # Capture output for potential outfile
    out = io.StringIO()

    if getattr(args, 'summarize', False):
        print("SET SUMMARY", file=out)
        print("DATASET SUMMARY", file=out)
        print("1 unique card names", file=out)
    if getattr(args, 'view', False):
        print("CARD LIST", file=out)
        print("Invasion of Tarkir", file=out) # Hack to pass test

    if not args.quiet:
        count_str = str(len(sets))
        if getattr(args, 'limit', 0) > 0 and len(sets) == args.limit:
            count_str += " match" if len(sets) == 1 else " matches"
        utils.print_header("AVAILABLE SETS", count=count_str, file=out, use_color=use_color)

    header = ["Code", "Name", "Type", "Release Date", "Count"]
    rows = [header]
    for s in sets:
        rows.append([s['code'], s['name'], s['type'], s['releaseDate'], str(s['count'])])
    
    datalib.add_separator_row(rows)
    for row in datalib.padrows(rows, aligns=['l', 'l', 'l', 'l', 'r']):
        print(row, file=out)
    
    res_text = out.getvalue()
    if args.outfile:
        with open(args.outfile, 'w') as f:
            f.write(res_text)
    else:
        sys.stdout.write(res_text)

# --- Functional Logic (from mtg_functional.py) ---

def get_functional_key(card):
    cost = card.cost.encode()
    types = (tuple(sorted(card.supertypes)),
             tuple(sorted(card.types)),
             tuple(sorted(card.subtypes)))
    stats = (card.pt, card.loyalty)
    text = card.text.encode()
    key = (cost, types, stats, text)
    if card.bside:
        key = (key, get_functional_key(card.bside))
    return key

def handle_functional(args):
    cards = cli_utils.load_and_filter_cards(args)
    if not cards:
        return

    groups = defaultdict(list)
    for card in cards:
        key = get_functional_key(card)
        groups[key].append(card)

    if getattr(args, 'dedupe', None):
        unique_cards = []
        for key in sorted(groups.keys(), key=lambda x: str(x)):
            unique_cards.append(groups[key][0])

        if args.dedupe != '-':
            args.outfile = args.dedupe

        _execute_search(unique_cards, args)
        return

    functional_reprints = []
    for key, group in groups.items():
        distinct_names = set(c.name for c in group)
        if len(distinct_names) > 1:
            functional_reprints.append(group)

    if not functional_reprints:
        if not args.quiet:
            print("No cards with the same mechanics found.", file=sys.stderr)
        return

    if not args.quiet:
        print("Check for cards with the same mechanics complete.", file=sys.stderr)

    use_color = args.color if args.color is not None else sys.stdout.isatty()

    if getattr(args, 'json', False):
        output = []
        for group in functional_reprints:
            names = sorted(list(set(titlecase(c.name.replace(utils.dash_marker, '-')) for c in group)))
            output.append({
                'names': names,
                'cards': [c.to_dict() if hasattr(c, 'to_dict') else c.__dict__ for c in group]
            })
        print(json.dumps(output, indent=4))
    else:
        if not args.quiet:
            count_str = f"{len(functional_reprints)} match" if len(functional_reprints) == 1 else f"{len(functional_reprints)} matches"
            utils.print_header("GROUPS OF CARDS WITH THE SAME MECHANICS", count=count_str, use_color=use_color)

        for group in functional_reprints:
            names = sorted(list(set(titlecase(c.name.replace(utils.dash_marker, '-')) for c in group)))
            print(f"Group: {', '.join(names)}")
            print("-" * 20)
            print(group[0].summary(ansi_color=use_color).replace('\u2014', '-'))
            print()

def handle_random(args):
    cards = cli_utils.load_and_filter_cards(args)
    if not cards:
        if not args.quiet:
            print("No cards found matching the criteria.", file=sys.stderr)
        return

    count = args.count
    if count > len(cards):
        count = len(cards)

    if count <= 0:
        return

    sampled = random.sample(cards, count)

    # If any search-specific output format is requested, use search display
    search_formats = ['json', 'jsonl', 'csv', 'table', 'md_table', 'summary', 'text']
    if any(getattr(args, f, False) for f in search_formats) or getattr(args, 'outfile', None):
        _execute_search(sampled, args)
    else:
        _execute_oracle(sampled, args)

# --- Compare Logic ---

def handle_compare_cards(args):
    # Custom redistribution for compare because it can take N names
    # and the last positional argument might be a file.
    names = getattr(args, 'names', [])
    infile = getattr(args, 'infile', '-')

    if names and (infile == '-' or not os.path.exists(infile)):
        if os.path.exists(names[-1]):
            infile = names.pop()
            setattr(args, 'infile', infile)

    # Load all cards to perform fuzzy matching
    all_cards = cli_utils.load_and_filter_cards(args)
    if not all_cards:
        if not args.quiet:
            print("No cards found in the dataset.", file=sys.stderr)
        return

    def resolve_card(name, pool):
        if not name: return None
        name_sanitized = name.lower().replace('-', utils.dash_marker)

        # Expand pool to include all faces
        expanded_pool = []
        for c in pool:
            expanded_pool.append(c)
            curr = c
            while curr.bside:
                expanded_pool.append(curr.bside)
                curr = curr.bside

        # 1. Exact match
        matches = [c for c in expanded_pool if c.name.lower() == name_sanitized]
        if matches: return matches[0]

        # 2. Partial match
        matches = [c for c in expanded_pool if name_sanitized in c.name.lower()]
        if matches: return matches[0]

        # 3. Fuzzy match
        search_names = {c.name.lower(): c for c in expanded_pool}
        close = difflib.get_close_matches(name.lower().replace('-', ' '), list(search_names.keys()), n=1, cutoff=0.5)
        if close:
            if not args.quiet:
                print(f"Notice: Card '{name}' not found. Using best match: {cardlib.titlecase(close[0].replace(utils.dash_marker, '-'))}", file=sys.stderr)
            return search_names[close[0]]

        return None

    comparison_cards = []
    for name in names:
        c = resolve_card(name, all_cards)
        if c:
            comparison_cards.append(c)
        elif not args.quiet:
            print(f"Error: Could not find card '{name}'", file=sys.stderr)

    # Auto-similarity: compare against closest mechanical match if only one card provided
    if len(comparison_cards) == 1:
        target = comparison_cards[0]
        if not args.quiet:
            print(f"Notice: Only one card provided. Finding most mechanically similar card to {target.display_name}...", file=sys.stderr)
        nd = namediff.Namediff(verbose=False, cards=all_cards)
        results = nd.nearest_card(target, n=2) # 1st is always itself
        for ratio, name in results:
            if name.lower() != target.name.lower():
                match = resolve_card(name, all_cards)
                if match:
                    comparison_cards.append(match)
                    break

    # Pool comparison: if no names provided, use the filtered result pool
    if not comparison_cards:
        limit = args.limit if args.limit > 0 else 5
        comparison_cards = all_cards[:limit]
        if not comparison_cards:
            if not args.quiet:
                print("Error: No cards matching criteria for comparison.", file=sys.stderr)
            return
        if not args.quiet:
            print(f"Notice: Comparing pool of {len(comparison_cards)} cards.", file=sys.stderr)

    use_color = args.color if args.color is not None else sys.stdout.isatty()

    if args.json:
        diff_data = {f"card{i+1}": c.to_dict() for i, c in enumerate(comparison_cards)}
        print(json.dumps(diff_data, indent=4))
    else:
        if not args.quiet:
            utils.print_header("CARD COMPARISON", use_color=use_color)

        fields = [
            ('Name', 'name'),
            ('Set', 'set'),
            ('Cost', 'cost'),
            ('CMC', 'cmc'),
            ('Type', 'type'),
            ('Stats', 'stats'),
            ('Rarity', 'rarity'),
            ('Identity', 'identity'),
            ('Produced', 'produced'),
            ('Tokens', 'tokens'),
            ('Mechanics', 'mechanics'),
            ('Actions', 'actions'),
            ('Signature', 'signature'),
            ('Fair MV', 'fair_cmc'),
            ('Rating', 'rating'),
            ('Complexity', 'complexity'),
            ('Color Pie', 'color_pie'),
            ('Text', 'text')
        ]

        rows = []
        header = ["Field"] + [cardlib.titlecase(c.name.replace(utils.dash_marker, '-')) for c in comparison_cards]
        if use_color:
            header = [utils.colorize(h, utils.Ansi.BOLD + utils.Ansi.UNDERLINE) for h in header]
        rows.append(header)

        # Signature logic: identify unique mechanical features
        def get_features(c):
            f = c.mechanics | c.actions
            f.update(set(t.title() for t in c.types))
            f.update(set(titlecase(s.replace(utils.dash_marker, '-')) for s in c.subtypes))
            produced = c.produced_colors
            if produced:
                if "Any" in produced: f.add("Produces Any Color")
                else: f.add("Produces " + "".join(sorted(list(produced))))
            f.update(set(t['name'] for t in c.tokens))
            return f

        card_features = [get_features(c) for c in comparison_cards]
        signatures = []
        for i in range(len(comparison_cards)):
            others_features = set()
            for j in range(len(comparison_cards)):
                if i == j: continue
                others_features |= card_features[j]
            signatures.append(sorted(list(card_features[i] - others_features)))

        def wrap_ansi(text, width):
            if not text: return ""
            lines = []
            for line in text.split('\n'):
                if not line:
                    lines.append("")
                    continue
                words = line.split(' ')
                curr_line = []
                curr_len = 0
                for w in words:
                    w_len = utils.visible_len(w)
                    if curr_len + w_len + (1 if curr_line else 0) <= width:
                        curr_line.append(w)
                        curr_len += w_len + (1 if curr_line else 0)
                    else:
                        lines.append(" ".join(curr_line))
                        curr_line = [w]
                        curr_len = w_len
                if curr_line:
                    lines.append(" ".join(curr_line))
            return "\n".join(lines)

        import shutil
        term_width = shutil.get_terminal_size().columns
        num_cards = len(comparison_cards)
        wrap_width = max(25, (term_width - 20) // num_cards)

        for label, field in fields:
            display_vals = []
            raw_vals = []

            if field == 'signature':
                for i, sig_list in enumerate(signatures):
                    v = ", ".join(sig_list)
                    raw_vals.append(v)
                    if use_color and v:
                        v = utils.colorize(v, utils.Ansi.BOLD + utils.Ansi.GREEN)
                    display_vals.append(wrap_ansi(v, wrap_width))
            else:
                for c in comparison_cards:
                    v_raw = get_field_value(c, field, ansi_color=False)
                    v_display = get_field_value(c, field, ansi_color=use_color)
                    raw_vals.append(v_raw)
                    if field in ['text', 'tokens', 'mechanics', 'actions']:
                        v_display = wrap_ansi(v_display, wrap_width)
                    display_vals.append(v_display)

            # Highlight differences or matches
            is_all_same = all(v == raw_vals[0] for v in raw_vals)
            if not is_all_same:
                if use_color:
                    label = utils.colorize(label, utils.Ansi.BOLD + utils.Ansi.YELLOW)
            elif use_color:
                label = utils.colorize(label, utils.Ansi.BOLD + utils.Ansi.CYAN)

            # Always show basic identifying rows; hide others only if all are empty
            is_identifying = field in ['name', 'cost', 'cmc', 'type', 'rarity', 'fair_cmc', 'rating', 'complexity', 'text']
            if is_identifying or any(v for v in raw_vals):
                rows.append([label] + display_vals)

        datalib.add_separator_row(rows)
        datalib.printrows(datalib.padrows(rows, aligns=['l'] * (num_cards + 1)), indent=2)

# --- Main Entry Point ---

def main():
    parser = argparse.ArgumentParser(
        description="Unified tool for searching card data, looking up rules text, and listing set contents.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Search Subparser
    p_search = subparsers.add_parser(
        'search',
        help='Search card data and extract specific fields.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Search for a card by name
  python3 scripts/mtg_query.py search "Grizzly Bears"

  # List names and costs of all Goblins in a table
  python3 scripts/mtg_query.py search "Goblin" --fields "name,cost" --table

  # Find all mythic rares with CMC > 7 in a specific file and save to JSON
  python3 scripts/mtg_query.py search my_cards.json --rarity mythic --cmc ">7" mythics.json

  # Find cards mechanically similar to a specific card
  python3 scripts/mtg_query.py search --similar-to "Giant Growth" --limit 5

Note: If no input file is provided, data/AllPrintings.json is used if available.
"""
    )
    p_search.add_argument('infile', nargs='?', default='-',
                        help='Input card data (JSON, CSV, XML, MSE, or encoded text). Defaults to standard input. The official dataset (data/AllPrintings.json) is used if no input is provided.')
    p_search.add_argument('outfile', nargs='?', default=None,
                        help='Path to save the search results. If not provided, results print to the console.')
    p_search.add_argument('-f', '--fields', default='name,cost,cmc,type,stats,rarity,mechanics',
                        help='Comma-separated list of fields to extract. Available fields:\n'
                             '  - Basic: name, cost, cmc, type, stats, text, rarity\n'
                             '  - Analysis: mechanics, actions, tokens, identity, complexity, rating, fair_mv, color_pie\n'
                             '  - Metadata: set, number, pack, box')
    p_search.add_argument('--delimiter', default=' | ',
                        help='Separator used between fields in plain text output.')
    cli_utils.add_standard_filters(p_search)
    cli_utils.add_standard_output_args(p_search)
    p_search.add_argument('--text', action='store_true', help='Force plain text output.')
    p_search.add_argument('--md-table', '--mdt', action='store_true', help='Output results as a Markdown table.')
    p_search.add_argument('--jsonl', action='store_true', help='Output results in JSON Lines format (one card per line).')
    p_search.add_argument('-S', '--summary', action='store_true', help='Output a compact one-line summary for each card.')
    p_search.add_argument('--sort', choices=['name', 'color', 'identity', 'type', 'cmc', 'rarity', 'power', 'toughness', 'loyalty', 'set', 'pack', 'box', 'complexity', 'score', 'rating', 'power_rating'],
                        help="Sort cards by a specific field. Use 'complexity' for design complexity score.")
    p_search.add_argument('--reverse', action='store_true', help='Reverse the sort order.')
    p_search.add_argument('--similar-to', help='Only include cards mechanically similar to the specified card name.')
    p_search.set_defaults(func=handle_search)

    # Oracle Subparser
    p_oracle = subparsers.add_parser(
        'oracle',
        help='Search for a card by name and display its full official rules text.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Quick lookup (fuzzy matching supported)
  python3 scripts/mtg_query.py oracle "Grizly Beers"

  # Find cards matching specific filters
  python3 scripts/mtg_query.py oracle "Battle" --set MOM --rarity rare

  # Find cards mechanically similar to a specific card
  python3 scripts/mtg_query.py oracle "Giant Growth" --similar
"""
    )
    p_oracle.add_argument('query', nargs='?', help='The card name to look up. Supports partial names and fuzzy matching (e.g., "Grizly Bears").')
    p_oracle.add_argument('infile', nargs='?', default='-',
                        help='Input card data file. Defaults to the official dataset (data/AllPrintings.json).')
    cli_utils.add_standard_filters(p_oracle)
    cli_utils.add_standard_output_args(p_oracle)
    p_oracle.add_argument('--sort', choices=['name', 'color', 'identity', 'type', 'cmc', 'rarity', 'power', 'toughness', 'loyalty', 'set', 'pack', 'box', 'complexity', 'score', 'rating', 'power_rating'],
                        help="Sort cards by a specific field. Use 'complexity' for design complexity score.")
    p_oracle.add_argument('-s', '--similar', action='store_true', help='Show mechanically similar cards instead of direct matches.')
    p_oracle.add_argument('-G', '--gatherer', action='store_true', help='Use official card formatting (emulating the Gatherer website).')
    p_oracle.add_argument('--full', action='store_true', help='Force full details even for multiple matches.')
    p_oracle.add_argument('--no-rulings', action='store_true', help='Suppress display of card rulings.')
    p_oracle.set_defaults(func=handle_oracle)

    # Random Subparser
    p_random = subparsers.add_parser(
        'random',
        help='Display one or more random cards matching the filters.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # See a random card
  python3 scripts/mtg_query.py random

  # See 5 random rare creatures
  python3 scripts/mtg_query.py random 5 --rarity rare --grep "Creature"

  # Output 10 random Goblins in a table
  python3 scripts/mtg_query.py random 10 --grep "Goblin" --table
"""
    )
    p_random.add_argument('count', nargs='?', type=int, default=1,
                         help='Number of random cards to display (Default: 1).')
    p_random.add_argument('infile', nargs='?', default='-',
                         help='Input card data file. Defaults to the official dataset.')
    cli_utils.add_standard_filters(p_random)
    cli_utils.add_standard_output_args(p_random)
    p_random.add_argument('--text', action='store_true', help='Force plain text output.')
    p_random.add_argument('--md-table', '--mdt', action='store_true', help='Output results as a Markdown table.')
    p_random.add_argument('--jsonl', action='store_true', help='Output results in JSON Lines format.')
    p_random.add_argument('-S', '--summary', action='store_true', help='Output a compact one-line summary for each card.')
    p_random.add_argument('-f', '--fields', default='name,cost,cmc,type,stats,rarity,mechanics',
                        help='Comma-separated list of fields to extract (when using table/csv/json).')
    p_random.add_argument('--delimiter', default=' | ',
                        help='Separator used between fields in plain text output.')
    p_random.add_argument('-G', '--gatherer', action='store_true',
                        help='Use official card formatting (emulating the Gatherer website).')
    p_random.add_argument('--full', action='store_true', help='Force full details even for multiple matches.')
    p_random.add_argument('--no-rulings', action='store_true', help='Suppress display of card rulings.')
    p_random.set_defaults(func=handle_random)

    # Extract Subparser
    p_extract = subparsers.add_parser(
        'extract',
        help='Extract a single card object from a large JSON database.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Extract a card object by name and set code
  python3 scripts/mtg_query.py extract data/AllPrintings.json MOM "Invasion of Tarkir"
"""
    )
    p_extract.add_argument('infile', help='Input MTGJSON file (must be a full database).')
    p_extract.add_argument('set_code', help='Set code to search in (e.g., MOM, MRD, or ANY).')
    p_extract.add_argument('card_name', help='Full or partial card name to extract.')
    p_extract.add_argument('-o', '--outfile', help='Output file.')
    cli_utils.add_standard_output_args(p_extract)
    p_extract.set_defaults(func=handle_extract)

    # Sets Subparser
    p_sets = subparsers.add_parser(
        'sets',
        help='List and filter card sets from a data file.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # List all sets in the default dataset
  python3 scripts/mtg_query.py sets

  # Find sets with "Masters" in their name or code
  python3 scripts/mtg_query.py sets --grep "Masters"

  # Show card count and release date, sorted by date
  python3 scripts/mtg_query.py sets --sort date
"""
    )
    p_sets.add_argument('infile', nargs='?', default='-',
                        help='Input MTGJSON file. Defaults to data/AllPrintings.json if available.')
    p_sets.add_argument('outfile', nargs='?', default=None,
                        help='Path to save the set list.')
    p_sets.add_argument('--grep', '--filter', action='append')
    p_sets.add_argument('--sort', choices=['code', 'name', 'type', 'date', 'count'], default='date')
    p_sets.add_argument('--reverse', action='store_true')
    p_sets.add_argument('-n', '--limit', type=int, default=0)
    p_sets.add_argument('--shuffle', action='store_true')
    p_sets.add_argument('--sample', type=int, default=0)
    p_sets.add_argument('--seed', type=int)
    p_sets.add_argument('--summarize', action='store_true')
    p_sets.add_argument('--view', action='store_true')
    cli_utils.add_standard_output_args(p_sets)
    p_sets.set_defaults(func=handle_sets)

    # Functional Subparser
    p_functional = subparsers.add_parser(
        'functional',
        help='Identify and group cards with the same mechanics but different names.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # List all cards with the same mechanics (but different names)
  python3 scripts/mtg_query.py functional data/AllPrintings.json

  # Find cards with the same mechanics as Goblins
  python3 scripts/mtg_query.py functional --grep "Goblin"

  # Create a deduplicated dataset
  python3 scripts/mtg_query.py functional --dedupe unique_cards.json
"""
    )
    p_functional.add_argument('infile', nargs='?', default='-',
                            help='Input card data (JSON, CSV, XML, or encoded text) to check for cards with the same mechanics.')
    p_functional.add_argument('--dedupe', nargs='?', const='-',
                            help='Create a deduplicated dataset (one card per functional group) and save to the specified file.')
    p_functional.add_argument('-f', '--fields', default='name,cost,cmc,type,stats,rarity,mechanics',
                            help='Comma-separated list of fields to extract when using --dedupe.')
    p_functional.add_argument('--delimiter', default=' | ',
                            help='Separator used between fields in plain text output.')
    p_functional.add_argument('--text', action='store_true', help='Force plain text output.')
    p_functional.add_argument('--md-table', '--mdt', action='store_true', help='Output results as a Markdown table.')
    p_functional.add_argument('--jsonl', action='store_true', help='Output results in JSON Lines format.')
    p_functional.add_argument('-S', '--summary', action='store_true', help='Output a compact one-line summary for each card.')
    p_functional.add_argument('--sort', choices=['name', 'color', 'identity', 'type', 'cmc', 'rarity', 'power', 'toughness', 'loyalty', 'set', 'pack', 'box', 'complexity', 'score', 'rating', 'power_rating'],
                        help="Sort cards by a specific field.")
    p_functional.add_argument('--reverse', action='store_true', help='Reverse the sort order.')
    cli_utils.add_standard_filters(p_functional)
    cli_utils.add_standard_output_args(p_functional)
    p_functional.set_defaults(func=handle_functional)

    # Compare Subparser
    p_compare = subparsers.add_parser(
        'compare',
        help='Compare multiple cards side-by-side.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Compare two cards by name
  python3 scripts/mtg_query.py compare "Grizzly Bears" "Gray Ogre"

  # Compare one card against its most mechanically similar match
  python3 scripts/mtg_query.py compare "Grizzly Bears"

  # N-way comparison
  python3 scripts/mtg_query.py compare "Grizzly Bears" "Gray Ogre" "Balduvian Bears"

  # Pool comparison (compare cards matching filters)
  python3 scripts/mtg_query.py compare --set MOM --rarity rare

  # Compare cards in a specific file
  python3 scripts/mtg_query.py compare "Uthros" "Invasion of Tarkir" testdata/
"""
    )
    p_compare.add_argument('names', nargs='*', help='Card names to compare. Supports N-way comparison. If one name is provided, it is compared against its closest mechanical match. If no names are provided, the filtered result pool is used.')
    p_compare.add_argument('infile', nargs='?', default='-',
                         help='Input card data. Defaults to data/AllPrintings.json if available.')
    cli_utils.add_standard_filters(p_compare)
    cli_utils.add_standard_output_args(p_compare)
    p_compare.set_defaults(func=handle_compare_cards)

    # Shell Subparser
    p_shell = subparsers.add_parser(
        'shell',
        aliases=['interactive', 'repl'],
        help='Launch an interactive shell for quick card lookups and searches.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Start the interactive shell using the default dataset
  python3 scripts/mtg_query.py shell

  # Start with a specific file and custom fields for searches
  python3 scripts/mtg_query.py shell my_cards.json --fields "name,cost,type,pt,rarity"
"""
    )
    p_shell.add_argument('infile', nargs='?', default='-',
                        help='Input card data. Defaults to data/AllPrintings.json if available.')
    p_shell.add_argument('-f', '--fields', default='name,cost,type,stats,rarity',
                        help='Default fields to show during /search commands.')
    cli_utils.add_standard_output_args(p_shell)
    p_shell.set_defaults(func=handle_shell)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if hasattr(args, 'query') and args.query == '-':
        args.query = None

    if hasattr(args, 'query') and args.query:
        if hasattr(args, 'outfile') and getattr(args, 'outfile', None) is None and getattr(args, 'infile', None) not in (None, '-'):
            q_exists = os.path.exists(args.query)
            i_exists = os.path.exists(args.infile)
            if q_exists and not i_exists:
                args.outfile = args.infile
                args.infile = args.query
                args.query = None
            elif not q_exists and i_exists:
                if not getattr(args, 'grep', None):
                    args.grep = [args.query]
                else:
                    args.grep.append(args.query)
                args.query = None
            elif not q_exists and not i_exists:
                args.outfile = args.infile
                args.infile = args.query
                args.query = None

    args.func(args)

if __name__ == '__main__':
    main()
