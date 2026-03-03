import json
import sys
import os
import re
import csv
import zipfile
import random
import io

import utils
import cardlib

def mtg_open_csv_reader(reader, verbose = False):
    """
    Processes a CSV reader containing card data.
    """
    srcs = {}
    for row in reader:
        # Map CSV columns to JSON-style dict keys
        card_dict = {
            'name': row.get('name', ''),
            'manaCost': row.get('mana_cost', row.get('manaCost', '')),
            'text': row.get('text', ''),
            'rarity': row.get('rarity', ''),
        }
        if row.get('power'):
            card_dict['power'] = row['power']
        if row.get('toughness'):
            card_dict['toughness'] = row['toughness']
        if row.get('loyalty'):
            card_dict['loyalty'] = row['loyalty']
        elif row.get('defense'):
            card_dict['defense'] = row['defense']

        # Split type into supertypes and types
        full_type = row.get('type', '')
        supertypes, types = utils.split_types(full_type)
        card_dict['supertypes'] = supertypes
        card_dict['types'] = types

        # Subtypes
        subtypes = row.get('subtypes', '')
        if subtypes:
            card_dict['subtypes'] = subtypes.split()

        cardname = card_dict['name'].lower()
        if cardname in srcs:
            srcs[cardname].append(card_dict)
        else:
            srcs[cardname] = [card_dict]

    if verbose:
        print('Opened ' + str(len(srcs)) + ' uniquely named cards from CSV.', file=sys.stderr)

    return srcs, set()

def mtg_open_csv(fname, verbose = False):
    """
    Reads a CSV file containing card data.
    Supports the format exported by decode.py.
    """
    with open(fname, 'r', encoding='utf8', newline='') as f:
        reader = csv.DictReader(f)
        return mtg_open_csv_reader(reader, verbose)

def mtg_open_json_obj(jobj, verbose = False):
    """
    Processes a JSON object containing card data.

    Supported formats:
    1. MTGJSON v4/v5 format (dictionary with a 'data' key).
    2. A list of card objects.
    3. A single card object (detected if it's a dict without a 'data' key).

    Returns:
        tuple: (allcards, bad_sets)
            allcards: Dictionary mapping card names (lowercase) to lists of card objects.
            bad_sets: Set of set codes flagged as 'funny', 'memorabilia', or 'alchemy'.
    """

    is_mtgjson_format = isinstance(jobj, dict)
    if is_mtgjson_format:
        if 'data' in jobj:
            jobj = jobj['data']
        else:
            # Assume it is a single card object
            is_mtgjson_format = False
            jobj = [jobj]

    bad_sets = set()
    allcards = {}
    asides = {}
    bsides = {}

    if is_mtgjson_format:
        for set_data in jobj.values():
            setname = set_data['name']
            # flag sets that should be excluded by default, like funny and art card sets
            if (set_data['type'] in ['funny', 'memorabilia', 'alchemy']):
                bad_sets.add(set_data['code'])
            codename = set_data.get('magicCardsInfoCode', '')

            for card in set_data['cards']:
                card[utils.json_field_set_name] = setname
                card[utils.json_field_info_code] = codename
                card['setCode'] = set_data['code']

                cardnumber = None
                if 'number' in card:
                    cardnumber = card['number']
                # the lower avoids duplication of at least one card (Will-o/O'-the-Wisp)
                cardname = card['name'].lower()

                uid = set_data['code']
                if cardnumber == None:
                    uid = uid + '_' + cardname + '_'
                else:
                    uid = uid + '_' + cardnumber

                # aggregate by name to avoid duplicates, not counting bsides
                if not uid[-1] == 'b':
                    if cardname in allcards:
                        allcards[cardname] += [card]
                    else:
                        allcards[cardname] = [card]

                # also aggregate aside cards by uid so we can add bsides later
                if uid[-1:] == 'a':
                    asides[uid] = card
                if uid[-1:] == 'b':
                    bsides[uid] = card
    else: # It is a list of cards
        for card in jobj:
            cardname = card['name'].lower()
            if cardname in allcards:
                allcards[cardname] += [card]
            else:
                allcards[cardname] = [card]

    if verbose:
        print('Opened ' + str(len(allcards)) + ' uniquely named cards.', file=sys.stderr)

    for uid in bsides:
        aside_uid = uid[:-1] + 'a'
        if aside_uid in asides:
            # the second check handles the brothers yamazaki edge case
            if not asides[aside_uid]['name'] == bsides[uid]['name']:
                asides[aside_uid][utils.json_field_bside] = bsides[uid]
        else:
            pass
            # this exposes some coldsnap theme deck bsides that aren't
            # really bsides; shouldn't matter too much
            #print aside_uid
            #print bsides[uid]

    return allcards, bad_sets

def mtg_open_json(fname, verbose = False):
    """
    Reads a JSON file containing card data.
    """
    with open(fname, 'r', encoding='utf8') as f:
        jobj = json.load(f)
    return mtg_open_json_obj(jobj, verbose)

def mtg_open_jsonl_content(text, verbose = False):
    """
    Processes JSON Lines (.jsonl) content.
    """
    cards = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            try:
                cards.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if cards:
        return mtg_open_json_obj(cards, verbose)
    return {}, set()

def mtg_open_jsonl(fname, verbose = False):
    """
    Reads a JSON Lines (.jsonl) file containing card data.
    Each line should be a single card object.
    """
    with open(fname, 'r', encoding='utf8') as f:
        text = f.read()
    return mtg_open_jsonl_content(text, verbose)

def mtg_open_mse(fname, verbose = False):
    """
    Reads a Magic Set Editor (.mse-set) file.
    """
    with zipfile.ZipFile(fname, 'r') as zf:
        try:
            with zf.open('set') as f:
                content = f.read().decode('utf-8')
        except KeyError:
            if verbose:
                print(f"Warning: 'set' file not found in {fname}", file=sys.stderr)
            return {}, set()

    return mtg_open_mse_content(content, verbose=verbose)

def parse_decklist(fpath):
    """
    Parses a standard MTG decklist file.
    Returns a dictionary mapping lowercase card names to counts.
    """
    name_counts = {}
    if not os.path.exists(fpath):
        return name_counts

    # Standard MTG decklist line: [Count] Name [(Set)] [Number]
    # Example: 4 Grizzly Bears (LEA) 201
    # We want to be lenient and capture the name primarily.
    # Note: Some names can contain dashes or other symbols.
    with open(fpath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines, comments, and standard decklist separators
            if not line or line.startswith(('#', '//', 'Sideboard', 'Deck')):
                continue

            # Match count and name
            # Optional count at start (digits followed by space or 'x' and space)
            # followed by name. Name ends before a '(' or '[' or '#' (comment).
            match = re.match(r'^(\d+[xX]?\s+)?([^(\[\n#]+)', line)
            if match:
                count_str = match.group(1)
                name = match.group(2).strip()

                count = 1
                if count_str:
                    # Clean up the count string
                    count_str = count_str.strip().lower().replace('x', '')
                    try:
                        count = int(count_str)
                    except ValueError:
                        count = 1

                name_lower = name.lower()
                # Exclude common non-card words that might slip through
                if name_lower in ['sideboard', 'deck', 'maybeboard']:
                    continue

                name_counts[name_lower] = name_counts.get(name_lower, 0) + count
    return name_counts

def mtg_open_mse_content(content, verbose=False):
    """
    Parses the 'set' file content from an MSE archive.
    """
    allcards_raw = []
    lines = content.splitlines()

    current_card = None
    in_card = False

    def clean_mse_text(text):
        # Remove MSE tags like <sym-auto>
        text = re.sub(r'</?sym-auto>', '', text)
        return text.strip()

    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith('card:'):
            if current_card:
                allcards_raw.append(current_card)
            current_card = {}
            in_card = True
        elif in_card:
            if line.startswith('\t\t'):
                # Multi-line value (continuation)
                pass # Handled by the key-value branch below
            elif line.startswith('\t'):
                line = line[1:] # remove first tab
                if ': ' in line:
                    key, value = line.split(': ', 1)
                    if key in ['rule text', 'rule text 2']:
                        text_lines = [value]
                        while i + 1 < len(lines) and lines[i+1].startswith('\t\t'):
                            text_lines.append(lines[i+1][2:])
                            i += 1
                        current_card[key] = clean_mse_text('\n'.join(text_lines))
                    else:
                        current_card[key] = value.strip()
                elif line.endswith(':'):
                    key = line[:-1]
                    if key in ['rule text', 'rule text 2']:
                        text_lines = []
                        while i + 1 < len(lines) and lines[i+1].startswith('\t\t'):
                            text_lines.append(lines[i+1][2:])
                            i += 1
                        current_card[key] = clean_mse_text('\n'.join(text_lines))
                    else:
                        current_card[key] = ""
            elif line.strip() == '' or not line.startswith('\t'):
                # End of card block or irrelevant set info
                pass
        i += 1

    if current_card:
        allcards_raw.append(current_card)

    def mse_mana_to_json(s):
        if not s: return ""
        # Improved regex to handle hybrid costs like W/U, 2/W, W/U/B, and W/P
        tokens = re.findall(r'(?:[a-zA-Z0-9]/)+[a-zA-Z0-9]|\d+|[a-zA-Z]', s)
        res = ""
        for t in tokens:
            res += "{" + t.upper() + "}"
        return res

    allcards = {}
    for c in allcards_raw:
        # Main side
        d = {
            'name': c.get('name', ''),
            'manaCost': mse_mana_to_json(c.get('casting cost', '')),
            'rarity': c.get('rarity', '').capitalize(),
            'text': c.get('rule text', ''),
        }
        if c.get('power'): d['power'] = c['power']
        if c.get('toughness'): d['toughness'] = c['toughness']
        if c.get('loyalty'): d['loyalty'] = c['loyalty']
        if c.get('defense'): d['defense'] = c['defense']

        # Split types
        full_type = c.get('super type', '')
        supertypes, types = utils.split_types(full_type)
        d['supertypes'] = supertypes
        d['types'] = types

        subtypes = c.get('sub type', '')
        if subtypes:
            d['subtypes'] = subtypes.split()

        # Planeswalker loyalty costs
        if d.get('loyalty'):
            pw_abilities = []
            for j in range(1, 10):
                cost_key = f'loyalty cost {j}'
                if cost_key in c:
                    cost = c[cost_key]
                    # We assume abilities are separated by newlines in 'rule text'
                    # if they were exported by our to_mse
                    # But for general MSE, they might be in separate fields.
                    # Our to_mse puts them all in 'rule text'.
                    pass
            # Reconstructing PW text from loyalty costs and rule text is hard in general
            # but if it was exported by us, the costs are missing from 'rule text'.
            # However, Card.fields_from_json handles 'text' which should contain the costs.
            # So if we want it to work with our encoder, we should probably
            # try to put the costs back into the text if they are separate.
            # But wait, MSE's 'rule text' for PWs in our to_mse HAS the costs stripped.

        # Handle split card (B-side)
        if 'name 2' in c:
            b = {
                'name': c.get('name 2', ''),
                'manaCost': mse_mana_to_json(c.get('casting cost 2', '')),
                'rarity': c.get('rarity 2', d['rarity']).capitalize(),
                'text': c.get('rule text 2', ''),
            }
            if c.get('power 2'): b['power'] = c['power 2']
            if c.get('toughness 2'): b['toughness'] = c['toughness 2']
            if c.get('loyalty 2'): b['loyalty'] = c['loyalty 2']
            if c.get('defense 2'): b['defense'] = c['defense 2']
            full_type_2 = c.get('super type 2', '')
            supertypes_2, types_2 = utils.split_types(full_type_2)
            b['supertypes'] = supertypes_2
            b['types'] = types_2
            subtypes_2 = c.get('sub type 2', '')
            if subtypes_2:
                b['subtypes'] = subtypes_2.split()
            d[utils.json_field_bside] = b

        cardname = d['name'].lower()
        if cardname:
            if cardname in allcards:
                allcards[cardname].append(d)
            else:
                allcards[cardname] = [d]

    if verbose:
        print('Opened ' + str(len(allcards)) + ' uniquely named cards from MSE set.', file=sys.stderr)

    return allcards, set()

# filters to ignore some undesirable cards, only used when opening json
def default_exclude_sets(cardset):
    return cardset == 'Unglued' or cardset == 'Unhinged' or cardset == 'Celebration'

def default_exclude_types(cardtype):
    return cardtype in ['conspiracy', 'contraption']

def default_exclude_layouts(layout):
    return layout in ['token', 'planar', 'scheme', 'phenomenon', 'vanguard']

# centralized logic for opening files of cards, either encoded or json
def _find_best_candidate(jcards, exclude_sets, linetrans):
    # look for a normal rarity version, in a set we can use
    for idx, jcard in enumerate(jcards):
        card = cardlib.Card(jcard, linetrans=linetrans)
        if (card.rarity != utils.rarity_special_marker and
            not exclude_sets(jcard.get(utils.json_field_set_name))):
            return idx, card

    # if there isn't one, settle with index 0
    return 0, cardlib.Card(jcards[0], linetrans=linetrans)

def _check_parsing_quality(cards, report_fobj):
    good_count = 0
    bad_count = 0
    for card in cards:
        if not card.parsed and not card.text.text:
            bad_count += 1
        elif len(card.name) > 50 or len(card.rarity) > 3:
            bad_count += 1
        else:
            good_count += 1
        if good_count + bad_count > 15:
            break
    # random heuristic
    if bad_count > 10:
        print ('WARNING: Saw a bunch of unparsed cards:', file=sys.stderr)
        print ('         Is this a legacy format? You may need to specify the field order.', file=sys.stderr)
    if report_fobj:
        report_fobj.close()
    return cards

def _process_json_srcs(json_srcs, bad_sets, verbose, linetrans,
                       exclude_sets, exclude_types, exclude_layouts,
                       report_fobj, decklist_names=None):
    cards = []
    valid = 0
    skipped = 0
    invalid = 0
    unparsed = 0

    # If decklist is provided, we use it as our primary list of names to process
    if decklist_names:
        target_names = sorted(decklist_names.keys())
        if verbose:
            missing = [name for name in target_names if name not in json_srcs]
            if missing:
                print(f"Warning: {len(missing)} cards from decklist not found in source: {', '.join(missing[:5])}{'...' if len(missing) > 5 else ''}", file=sys.stderr)
    else:
        target_names = sorted(json_srcs)

    # sorted for stability
    for json_cardname in target_names:
        if json_cardname in json_srcs and len(json_srcs[json_cardname]) > 0:
            jcards = json_srcs[json_cardname]

            idx, card = _find_best_candidate(jcards, exclude_sets, linetrans)

            skip = False
            # Check exclusions
            # Note: _find_best_candidate returns a cardlib.Card object, but we also check jcards[idx] for raw fields
            # Checking set name and layout from raw json
            if (exclude_sets(jcards[idx].get(utils.json_field_set_name))
                or exclude_layouts(jcards[idx].get('layout'))
                or jcards[idx].get('setCode') in bad_sets):
                skip = True

            # Checking types from card object
            for cardtype in card.types:
                if exclude_types(cardtype):
                    skip = True

            if skip:
                skipped += 1
                continue

            if card.valid:
                # Handle multiplication from decklist
                count = decklist_names[json_cardname] if decklist_names else 1
                for _ in range(count):
                    valid += 1
                    cards += [card]
            elif card.parsed:
                invalid += 1
                if verbose:
                    print ('Invalid card: ' + json_cardname, file=sys.stderr)
            else:
                print(card.name, file=sys.stderr)
                unparsed += 1
                if report_fobj:
                    unparsed_card_repr = {
                        "name": card.name,
                        "fields": jcards[idx]
                    }
                    report_fobj.write(json.dumps(unparsed_card_repr, indent=2))

    if verbose:
        print((str(valid) + ' valid, ' + str(skipped) + ' skipped, '
               + str(invalid) + ' invalid, ' + str(unparsed) + ' failed to parse.'), file=sys.stderr)

    return cards

def _hydrate_decklist(decklist_names, verbose, linetrans,
                       exclude_sets, exclude_types, exclude_layouts, report_fobj):
    """
    Attempts to resolve card names in a decklist against data/AllPrintings.json.
    """
    default_data = os.path.join(os.path.dirname(__file__), '../data/AllPrintings.json')
    if os.path.exists(default_data):
        if verbose:
            print(f'Auto-hydrating decklist using {default_data}', file=sys.stderr)
        json_srcs, bad_sets = mtg_open_json(default_data, verbose=False)
        return _process_json_srcs(json_srcs, bad_sets, verbose, linetrans,
                                   exclude_sets, exclude_types, exclude_layouts, report_fobj,
                                   decklist_names=decklist_names)
    return []

def _process_text_cards(txt_cards, decklist_names, verbose, report_fobj=None):
    """
    Processes a list of Card objects from encoded text, applying decklist filters/multipliers.
    """
    cards = []
    valid = 0
    invalid = 0
    unparsed = 0

    def handle_card(card, count):
        nonlocal valid, invalid, unparsed
        for _ in range(count):
            cards.append(card)
            if card.valid:
                valid += 1
            elif card.parsed:
                invalid += 1
                if verbose:
                    print ('Invalid card: ' + (card.raw if card.raw else card.encode()), file=sys.stderr)
                if report_fobj:
                    report_fobj.write((card.raw if card.raw else card.encode()) + utils.cardsep)
            else:
                unparsed += 1
                if verbose:
                    print ('Failed to parse card: ' + (card.raw if card.raw else card.encode()), file=sys.stderr)
                if report_fobj:
                    report_fobj.write((card.raw if card.raw else card.encode()) + utils.cardsep)

    if decklist_names:
        name_to_txt_card = {}
        for c in txt_cards:
            name_l = c.name.lower()
            if name_l in decklist_names and name_l not in name_to_txt_card:
                name_to_txt_card[name_l] = c

        # Iterating over decklist names ensures we get the right counts and multiplication
        for name in sorted(decklist_names.keys()):
            if name in name_to_txt_card:
                card = name_to_txt_card[name]
                count = decklist_names[name]
                handle_card(card, count)
    else:
        for card in txt_cards:
            handle_card(card, 1)

    return cards, valid, invalid, unparsed

def mtg_open_file(fname, verbose = False,
                  linetrans = True, fmt_ordered = cardlib.fmt_ordered_default,
                  fmt_labeled = cardlib.fmt_labeled_default,
                  exclude_sets = default_exclude_sets,
                  exclude_types = default_exclude_types,
                  exclude_layouts = default_exclude_layouts,
                  report_file=None, grep=None, vgrep=None,
                  grep_name=None, vgrep_name=None,
                  grep_types=None, vgrep_types=None,
                  grep_text=None, vgrep_text=None,
                  grep_cost=None, vgrep_cost=None,
                  grep_pt=None, vgrep_pt=None,
                  grep_loyalty=None, vgrep_loyalty=None,
                  sets=None, rarities=None,
                  colors=None, cmcs=None,
                  shuffle=False, seed=None,
                  decklist_file=None):
    """
    High-level entry point for loading card data from various formats.
    Supported formats: JSON, JSONL, CSV, Magic Set Editor (.mse-set),
    and standard MTG decklists (.txt, .deck, .dek).

    Decklist support includes "auto-hydration": if a decklist is provided as
    the primary input and data/AllPrintings.json exists, the tool will
    automatically resolve card names into full Card objects.

    Returns a list of cardlib.Card objects.
    """

    cards = []
    valid = 0
    skipped = 0
    invalid = 0
    unparsed = 0
    txt_cards = []
    report_fobj = None
    if report_file:
        report_fobj = open(report_file, 'w', encoding='utf-8')

    decklist_names = None
    if decklist_file:
        decklist_names = parse_decklist(decklist_file)
        if verbose:
            print(f"Loaded decklist from {decklist_file} with {len(decklist_names)} unique cards.", file=sys.stderr)

    # Directory Handling
    if fname != '-' and (os.path.isdir(fname) or fname.endswith('.zip')):
        is_zip = fname.endswith('.zip')
        if verbose:
            if is_zip:
                print(f"Opening ZIP archive {fname}...", file=sys.stderr)
            else:
                print(f"Scanning directory {fname} for JSON/CSV/JSONL files...", file=sys.stderr)

        aggregated_srcs = {}
        aggregated_bad_sets = set()
        txt_cards = []

        def process_file_content(f, content, is_zip):
            # Inner helper to avoid duplication between ZIP and directory
            srcs, bad = {}, set()
            t_cards = []

            if f.endswith('.json') or f.endswith('.csv') or f.endswith('.jsonl') or f.endswith('.mse-set'):
                if f.endswith('.mse-set'):
                    # Nested ZIP handling
                    with zipfile.ZipFile(io.BytesIO(content if is_zip else open(f, 'rb').read()), 'r') as nested_zf:
                        try:
                            with nested_zf.open('set') as nested_f:
                                inner_content = nested_f.read().decode('utf-8')
                            srcs, bad = mtg_open_mse_content(inner_content, verbose=False)
                        except KeyError:
                            if verbose:
                                print(f"Warning: 'set' file not found in nested MSE file {f}", file=sys.stderr)
                elif f.endswith('.json'):
                    try:
                        jobj = json.loads(content if is_zip else open(f, 'r', encoding='utf8').read())
                        srcs, bad = mtg_open_json_obj(jobj, verbose=False)
                    except json.JSONDecodeError:
                        pass
                elif f.endswith('.jsonl'):
                    srcs, bad = mtg_open_jsonl_content(content if is_zip else open(f, 'r', encoding='utf8').read(), verbose=False)
                else: # .csv
                    reader = csv.DictReader(io.StringIO(content if is_zip else open(f, 'r', encoding='utf8').read()))
                    srcs, bad = mtg_open_csv_reader(reader, verbose=False)
            elif f.endswith('.txt'):
                text = content if is_zip else open(f, 'r', encoding='utf8').read()
                if utils.fieldsep in text:
                    for card_src in text.split(utils.cardsep):
                        if card_src:
                            card = cardlib.Card(card_src, fmt_ordered=fmt_ordered,
                                                fmt_labeled=fmt_labeled, linetrans=linetrans)
                            skip = False
                            for cardtype in card.types:
                                if exclude_types(cardtype):
                                    skip = True
                            if not skip:
                                t_cards.append(card)

            return srcs, bad, t_cards

        if is_zip:
            with zipfile.ZipFile(fname, 'r') as zf:
                files = sorted([f for f in zf.namelist() if not f.endswith('/') and (f.endswith('.json') or f.endswith('.csv') or f.endswith('.jsonl') or f.endswith('.mse-set') or f.endswith('.txt'))])
                for f in files:
                    if verbose:
                        print(f"  Loading {f} from ZIP...", file=sys.stderr)
                    with zf.open(f) as zfile:
                        content = zfile.read().decode('utf-8') if not f.endswith('.mse-set') else zfile.read()
                        srcs, bad, t_cards = process_file_content(f, content, True)
                        aggregated_bad_sets.update(bad)
                        for key, val in srcs.items():
                            if key in aggregated_srcs:
                                aggregated_srcs[key].extend(val)
                            else:
                                aggregated_srcs[key] = val
                        txt_cards.extend(t_cards)
        else:
            files = sorted([f for f in os.listdir(fname) if f.endswith('.json') or f.endswith('.csv') or f.endswith('.jsonl') or f.endswith('.mse-set') or f.endswith('.txt')])
            for f in files:
                if verbose:
                    print(f"Loading {f}...", file=sys.stderr)
                full_path = os.path.join(fname, f)
                # For directories, we don't read content here but let the helper do it
                srcs, bad, t_cards = process_file_content(full_path, None, False)
                aggregated_bad_sets.update(bad)
                for key, val in srcs.items():
                    if key in aggregated_srcs:
                        aggregated_srcs[key].extend(val)
                    else:
                        aggregated_srcs[key] = val
                txt_cards.extend(t_cards)

        if verbose:
             if aggregated_srcs:
                 if is_zip:
                     print('Opened ' + str(len(aggregated_srcs)) + ' uniquely named cards from JSON/CSV files inside ZIP.', file=sys.stderr)
                 else:
                     print('Opened ' + str(len(aggregated_srcs)) + ' uniquely named cards from JSON/CSV files.', file=sys.stderr)
             if txt_cards:
                 if is_zip:
                     print('Opened ' + str(len(txt_cards)) + ' cards from encoded text files inside ZIP.', file=sys.stderr)
                 else:
                     print('Opened ' + str(len(txt_cards)) + ' cards from encoded text files.', file=sys.stderr)

        cards = _process_json_srcs(aggregated_srcs, aggregated_bad_sets, verbose, linetrans,
                                   exclude_sets, exclude_types, exclude_layouts, report_fobj,
                                   decklist_names=decklist_names)
        # Combine with cards from encoded text files
        processed_txt, _, _, _ = _process_text_cards(txt_cards, decklist_names, verbose, report_fobj=report_fobj)
        cards.extend(processed_txt)

    # Single CSV File Handling
    elif fname.endswith('.csv'):
        if verbose:
            print('This looks like a csv file: ' + fname, file=sys.stderr)
        csv_srcs, bad_sets = mtg_open_csv(fname, verbose)

        cards = _process_json_srcs(csv_srcs, bad_sets, verbose, linetrans,
                                   exclude_sets, exclude_types, exclude_layouts, report_fobj,
                                   decklist_names=decklist_names)

    # Single JSONL File Handling
    elif fname.endswith('.jsonl'):
        if verbose:
            print('This looks like a jsonl file: ' + fname, file=sys.stderr)
        jsonl_srcs, bad_sets = mtg_open_jsonl(fname, verbose)

        cards = _process_json_srcs(jsonl_srcs, bad_sets, verbose, linetrans,
                                   exclude_sets, exclude_types, exclude_layouts, report_fobj,
                                   decklist_names=decklist_names)

    # Single MSE File Handling
    elif fname.endswith('.mse-set'):
        if verbose:
            print('This looks like an MSE set file: ' + fname, file=sys.stderr)
        mse_srcs, bad_sets = mtg_open_mse(fname, verbose)

        cards = _process_json_srcs(mse_srcs, bad_sets, verbose, linetrans,
                                   exclude_sets, exclude_types, exclude_layouts, report_fobj,
                                   decklist_names=decklist_names)

    # Encoded Text or Decklist File Handling
    elif fname == '-' or (not fname.endswith('.json') and not fname.endswith('.mse-set')):
        if fname == '-':
            text = sys.stdin.read()
            # Stdin Format Detection
            stripped = text.strip()

            # 1. Decklist Detection
            # If it looks like a decklist (starts with a count like "4 Grizzly Bears")
            # and isn't obviously encoded text (doesn't have field separators)
            if re.match(r'^\d+\s+', stripped) and utils.fieldsep not in stripped:
                if verbose:
                    print('Detected Decklist input from stdin.', file=sys.stderr)
                if not decklist_names:
                    # We save to a temp file because parse_decklist expects a path
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tf:
                        tf.write(text)
                        tf_path = tf.name
                    decklist_names = parse_decklist(tf_path)
                    os.remove(tf_path)

                cards = _hydrate_decklist(decklist_names, verbose, linetrans,
                                           exclude_sets, exclude_types, exclude_layouts, report_fobj)

            # 2. JSON / JSONL Detection
            if not cards and (stripped.startswith('{') or stripped.startswith('[')):
                try:
                    # Try regular JSON first
                    jobj = json.loads(text)
                    if verbose:
                        print('Detected JSON input from stdin.', file=sys.stderr)
                    json_srcs, bad_sets = mtg_open_json_obj(jobj, verbose)
                    cards = _process_json_srcs(json_srcs, bad_sets, verbose, linetrans,
                                               exclude_sets, exclude_types, exclude_layouts, report_fobj,
                                               decklist_names=decklist_names)
                except json.JSONDecodeError:
                    # Try JSONL
                    jsonl_srcs, bad_sets = mtg_open_jsonl_content(text, verbose)
                    if jsonl_srcs:
                        if verbose:
                            print('Detected JSONL input from stdin.', file=sys.stderr)
                        cards = _process_json_srcs(jsonl_srcs, bad_sets, verbose, linetrans,
                                                   exclude_sets, exclude_types, exclude_layouts, report_fobj,
                                                   decklist_names=decklist_names)
            # 3. CSV Detection
            if not cards and stripped.startswith('name,'):
                try:
                    reader = csv.DictReader(io.StringIO(text))
                    if verbose:
                        print('Detected CSV input from stdin.', file=sys.stderr)
                    csv_srcs, bad_sets = mtg_open_csv_reader(reader, verbose)
                    cards = _process_json_srcs(csv_srcs, bad_sets, verbose, linetrans,
                                               exclude_sets, exclude_types, exclude_layouts, report_fobj,
                                               decklist_names=decklist_names)
                except Exception:
                    pass
        else:
            # Check if it's a decklist file based on extension or content
            is_decklist = fname.endswith('.deck') or fname.endswith('.dek')
            if not is_decklist:
                try:
                    with open(fname, 'rt', encoding='utf8') as f:
                        # Check first few lines for decklist pattern
                        for _ in range(5):
                            line = f.readline()
                            if not line: break
                            if re.match(r'^\d+\s+', line.strip()):
                                is_decklist = True
                                break
                except UnicodeDecodeError:
                    pass

            if is_decklist and not decklist_names:
                if verbose:
                    print(f'Detected {fname} as a decklist.', file=sys.stderr)
                decklist_names = parse_decklist(fname)

                cards = _hydrate_decklist(decklist_names, verbose, linetrans,
                                           exclude_sets, exclude_types, exclude_layouts, report_fobj)

            if not cards:
                with open(fname, 'rt', encoding='utf8') as f:
                    text = f.read()

        if not cards:
            if verbose:
                print('Opening encoded card file: ' + ('<stdin>' if fname == '-' else fname), file=sys.stderr)

            for card_src in text.split(utils.cardsep):
                if card_src:
                    card = cardlib.Card(card_src, fmt_ordered=fmt_ordered,
                                        fmt_labeled=fmt_labeled, linetrans=linetrans)

                    # Apply exclusions to cards from encoded text
                    skip = False
                    for cardtype in card.types:
                        if exclude_types(cardtype):
                            skip = True

                    if not skip:
                        txt_cards.append(card)
                    else:
                        skipped += 1

            processed_txt, valid_txt, invalid_txt, unparsed_txt = _process_text_cards(txt_cards, decklist_names, verbose, report_fobj=report_fobj)
            cards.extend(processed_txt)
            valid += valid_txt
            invalid += invalid_txt
            unparsed += unparsed_txt

            if verbose:
                 print((str(valid) + ' valid, ' + str(skipped) + ' skipped, '
                        + str(invalid) + ' invalid, ' + str(unparsed) + ' failed to parse.'), file=sys.stderr)

    # Single JSON File Handling
    else:
        if verbose:
            print('This looks like a json file: ' + fname, file=sys.stderr)
        json_srcs, bad_sets = mtg_open_json(fname, verbose)

        cards = _process_json_srcs(json_srcs, bad_sets, verbose, linetrans,
                                   exclude_sets, exclude_types, exclude_layouts, report_fobj,
                                   decklist_names=decklist_names)

    if grep or vgrep or sets or rarities or grep_name or vgrep_name or grep_types or vgrep_types or grep_text or vgrep_text or grep_cost or vgrep_cost or grep_pt or vgrep_pt or grep_loyalty or vgrep_loyalty or colors or cmcs:
        greps = [re.compile(p, re.IGNORECASE) for p in (grep if grep else [])]
        vgreps = [re.compile(p, re.IGNORECASE) for p in (vgrep if vgrep else [])]
        greps_name = [re.compile(p, re.IGNORECASE) for p in (grep_name if grep_name else [])]
        vgreps_name = [re.compile(p, re.IGNORECASE) for p in (vgrep_name if vgrep_name else [])]
        greps_types = [re.compile(p, re.IGNORECASE) for p in (grep_types if grep_types else [])]
        vgreps_types = [re.compile(p, re.IGNORECASE) for p in (vgrep_types if vgrep_types else [])]
        greps_text = [re.compile(p, re.IGNORECASE) for p in (grep_text if grep_text else [])]
        vgreps_text = [re.compile(p, re.IGNORECASE) for p in (vgrep_text if vgrep_text else [])]
        greps_cost = [re.compile(p, re.IGNORECASE) for p in (grep_cost if grep_cost else [])]
        vgreps_cost = [re.compile(p, re.IGNORECASE) for p in (vgrep_cost if vgrep_cost else [])]
        greps_pt = [re.compile(p, re.IGNORECASE) for p in (grep_pt if grep_pt else [])]
        vgreps_pt = [re.compile(p, re.IGNORECASE) for p in (vgrep_pt if vgrep_pt else [])]
        greps_loyalty = [re.compile(p, re.IGNORECASE) for p in (grep_loyalty if grep_loyalty else [])]
        vgreps_loyalty = [re.compile(p, re.IGNORECASE) for p in (vgrep_loyalty if vgrep_loyalty else [])]

        target_sets = [s.upper() for s in sets] if sets else None
        target_rarities = []
        target_rarities_lower = [r.lower() for r in rarities] if rarities else None
        if rarities:
            for r in rarities:
                r_lower = r.lower()
                if r_lower in utils.json_rarity_map:
                    target_rarities.append(utils.json_rarity_map[r_lower])
                else:
                    target_rarities.append(r)

        target_colors = [c.upper() for c in colors] if colors else None
        target_cmcs = [float(c) for c in cmcs] if cmcs else None

        def match_card(card):
            # Generic filtering (AND logic for greps, OR logic for vgreps)
            for pattern in greps:
                if not card.search(pattern):
                    return False
            for pattern in vgreps:
                if card.search(pattern):
                    return False

            # Name filtering
            for pattern in greps_name:
                if not card.search_name(pattern):
                    return False
            for pattern in vgreps_name:
                if card.search_name(pattern):
                    return False

            # Type filtering
            for pattern in greps_types:
                if not card.search_types(pattern):
                    return False
            for pattern in vgreps_types:
                if card.search_types(pattern):
                    return False

            # Text filtering
            for pattern in greps_text:
                if not card.search_text(pattern):
                    return False
            for pattern in vgreps_text:
                if card.search_text(pattern):
                    return False

            # Cost filtering
            for pattern in greps_cost:
                if not card.search_cost(pattern):
                    return False
            for pattern in vgreps_cost:
                if card.search_cost(pattern):
                    return False

            # P/T filtering
            for pattern in greps_pt:
                if not card.search_pt(pattern):
                    return False
            for pattern in vgreps_pt:
                if card.search_pt(pattern):
                    return False

            # Loyalty filtering
            for pattern in greps_loyalty:
                if not card.search_loyalty(pattern):
                    return False
            for pattern in vgreps_loyalty:
                if card.search_loyalty(pattern):
                    return False

            # Set filtering
            if target_sets:
                # If the card has no set code (like from an encoded text file),
                # we don't filter it out by set.
                if card.set_code and card.set_code.upper() not in target_sets:
                    return False

            # Rarity filtering
            if target_rarities:
                if not card.rarity:
                    return False
                if card.rarity not in target_rarities and card.rarity.lower() not in target_rarities_lower:
                    return False

            # Color filtering
            if target_colors:
                card_colors = card.cost.colors
                match_color = False
                for tc in target_colors:
                    if tc in ['A', 'C']:
                        if not card_colors: match_color = True
                    elif tc in card_colors:
                        match_color = True
                if not match_color:
                    return False

            # CMC filtering
            if target_cmcs:
                if card.cost.cmc not in target_cmcs:
                    return False

            return True
        cards = [c for c in cards if match_card(c)]

    if shuffle:
        if seed is not None:
            random.seed(seed)
        random.shuffle(cards)

    return _check_parsing_quality(cards, report_fobj)
