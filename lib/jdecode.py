import json
import sys
import os
import re
import csv

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
        supertypes = []
        types = []
        # Standard MTG supertypes
        known_supertypes = {'Legendary', 'Basic', 'Snow', 'World', 'Ongoing'}
        for t in full_type.split():
            if t in known_supertypes:
                supertypes.append(t)
            else:
                types.append(t)
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
                       report_fobj):
    cards = []
    valid = 0
    skipped = 0
    invalid = 0
    unparsed = 0

    # sorted for stability
    for json_cardname in sorted(json_srcs):
        if len(json_srcs[json_cardname]) > 0:
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

def mtg_open_file(fname, verbose = False,
                  linetrans = True, fmt_ordered = cardlib.fmt_ordered_default,
                  exclude_sets = default_exclude_sets,
                  exclude_types = default_exclude_types,
                  exclude_layouts = default_exclude_layouts,
                  report_file=None, grep=None):

    cards = []
    valid = 0
    skipped = 0
    invalid = 0
    unparsed = 0
    report_fobj = None
    if report_file:
        report_fobj = open(report_file, 'w', encoding='utf-8')

    # Directory Handling
    if fname != '-' and os.path.isdir(fname):
        if verbose:
            print(f"Scanning directory {fname} for JSON/CSV files...", file=sys.stderr)

        aggregated_srcs = {}
        aggregated_bad_sets = set()

        # Look for .json, .csv, and .txt files
        files = sorted([f for f in os.listdir(fname) if f.endswith('.json') or f.endswith('.csv') or f.endswith('.txt')])

        txt_cards = []
        for f in files:
            full_path = os.path.join(fname, f)
            if verbose:
                print(f"Loading {f}...", file=sys.stderr)

            if f.endswith('.json') or f.endswith('.csv'):
                if f.endswith('.json'):
                    srcs, bad = mtg_open_json(full_path, verbose=False)
                else:
                    srcs, bad = mtg_open_csv(full_path, verbose=False)
                aggregated_bad_sets.update(bad)
                for key, val in srcs.items():
                    if key in aggregated_srcs:
                        aggregated_srcs[key].extend(val)
                    else:
                        aggregated_srcs[key] = val
            elif f.endswith('.txt'):
                # Encoded text files are processed directly into Card objects
                with open(full_path, 'rt', encoding='utf8') as f_txt:
                    text = f_txt.read()

                # Heuristic to avoid loading non-card text files:
                # Must contain at least one field separator
                if utils.fieldsep not in text:
                    continue

                for card_src in text.split(utils.cardsep):
                    if card_src:
                        card = cardlib.Card(card_src, fmt_ordered=fmt_ordered, linetrans=linetrans)

                        # Apply exclusions to cards from encoded text
                        skip = False
                        for cardtype in card.types:
                            if exclude_types(cardtype):
                                skip = True

                        if not skip:
                            txt_cards.append(card)

        if verbose:
             if aggregated_srcs:
                 print('Opened ' + str(len(aggregated_srcs)) + ' uniquely named cards from JSON/CSV files.', file=sys.stderr)
             if txt_cards:
                 print('Opened ' + str(len(txt_cards)) + ' cards from encoded text files.', file=sys.stderr)

        cards = _process_json_srcs(aggregated_srcs, aggregated_bad_sets, verbose, linetrans,
                                   exclude_sets, exclude_types, exclude_layouts, report_fobj)
        # Combine with cards from encoded text files
        cards.extend(txt_cards)

    # Single CSV File Handling
    elif fname.endswith('.csv'):
        if verbose:
            print('This looks like a csv file: ' + fname, file=sys.stderr)
        csv_srcs, bad_sets = mtg_open_csv(fname, verbose)

        cards = _process_json_srcs(csv_srcs, bad_sets, verbose, linetrans,
                                   exclude_sets, exclude_types, exclude_layouts, report_fobj)

    # Encoded Text File Handling
    elif fname == '-' or not fname.endswith('.json'):
        if fname == '-':
            text = sys.stdin.read()
            # Stdin Format Detection
            stripped = text.strip()
            # 1. JSON Detection
            if stripped.startswith('{') or stripped.startswith('['):
                try:
                    jobj = json.loads(text)
                    if verbose:
                        print('Detected JSON input from stdin.', file=sys.stderr)
                    json_srcs, bad_sets = mtg_open_json_obj(jobj, verbose)
                    return _process_json_srcs(json_srcs, bad_sets, verbose, linetrans,
                                               exclude_sets, exclude_types, exclude_layouts, report_fobj)
                except json.JSONDecodeError:
                    pass
            # 2. CSV Detection
            if stripped.startswith('name,'):
                try:
                    import io
                    reader = csv.DictReader(io.StringIO(text))
                    if verbose:
                        print('Detected CSV input from stdin.', file=sys.stderr)
                    csv_srcs, bad_sets = mtg_open_csv_reader(reader, verbose)
                    return _process_json_srcs(csv_srcs, bad_sets, verbose, linetrans,
                                               exclude_sets, exclude_types, exclude_layouts, report_fobj)
                except Exception:
                    pass
        else:
            with open(fname, 'rt', encoding='utf8') as f:
                text = f.read()

        if verbose:
            print('Opening encoded card file: ' + ('<stdin>' if fname == '-' else fname), file=sys.stderr)

        for card_src in text.split(utils.cardsep):
            if card_src:
                card = cardlib.Card(card_src, fmt_ordered=fmt_ordered, linetrans=linetrans)

                # Apply exclusions to cards from encoded text
                skip = False
                for cardtype in card.types:
                    if exclude_types(cardtype):
                        skip = True

                if skip:
                    skipped += 1
                    continue

                # unlike opening from json, we still want to return invalid cards
                cards += [card]
                if card.valid:
                    valid += 1
                elif card.parsed:
                    invalid += 1
                    if verbose:
                        print ('Invalid card: ' + card_src, file=sys.stderr)
                    if report_fobj:
                        report_fobj.write(card_src + utils.cardsep)
                else:
                    unparsed += 1
                    if verbose:
                        print ('Failed to parse card: ' + card_src, file=sys.stderr)
                    if report_fobj:
                        report_fobj.write(card_src + utils.cardsep)

        if verbose:
             print((str(valid) + ' valid, ' + str(skipped) + ' skipped, '
                    + str(invalid) + ' invalid, ' + str(unparsed) + ' failed to parse.'), file=sys.stderr)

    # Single JSON File Handling
    else:
        if verbose:
            print('This looks like a json file: ' + fname, file=sys.stderr)
        json_srcs, bad_sets = mtg_open_json(fname, verbose)

        cards = _process_json_srcs(json_srcs, bad_sets, verbose, linetrans,
                                   exclude_sets, exclude_types, exclude_layouts, report_fobj)

    if grep:
        greps = [re.compile(p, re.IGNORECASE) for p in grep]
        def match_card(card):
            for pattern in greps:
                found = False
                if pattern.search(card.name): found = True
                elif any(pattern.search(t) for t in card.types): found = True
                elif any(pattern.search(t) for t in card.supertypes): found = True
                elif any(pattern.search(t) for t in card.subtypes): found = True
                elif pattern.search(card.text.text): found = True

                if not found:
                    return False
            return True
        cards = [c for c in cards if match_card(c)]

    return _check_parsing_quality(cards, report_fobj)
