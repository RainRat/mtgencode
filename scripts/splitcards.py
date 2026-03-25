#!/usr/bin/env python3
import sys
import os
import argparse
import json
import csv

# Ensure lib is in path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)
import jdecode
import utils
import cardlib
import sortlib

def main():
    parser = argparse.ArgumentParser(description="Splits a card dataset into multiple files (e.g., train, validation, test).")

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', help='Input card data (JSON, JSONL, CSV, MSE, ZIP, or encoded text).')
    io_group.add_argument('--outputs', nargs='+', required=True,
                        help='Output filenames for each split (e.g., train.txt val.txt).')
    io_group.add_argument('--ratios', type=float, nargs='+', required=True,
                        help='Ratios for each split (e.g., 0.9 0.1). Must match the number of outputs and sum to 1.0.')

    # Group: Output Format
    fmt_group = parser.add_argument_group('Output Format')
    fmt_group.add_argument('-f', '--format', choices=['text', 'json', 'jsonl', 'csv'], default='text',
                        help='Output format for the splits (default: text).')
    fmt_group.add_argument('-e', '--encoding', default='std', choices=utils.formats,
                        help="The encoding format to use if output is text: 'std' (default), 'named', 'noname', 'rfields', 'old', 'norarity', 'vec', or 'custom'.")
    fmt_group.add_argument('--nolabel', action='store_true',
                        help="Remove field labels (like '|cost|' or '|text|') from text output.")
    fmt_group.add_argument('--nolinetrans', action='store_true',
                        help='Keep the original order of card text lines (disable automatic reordering).')

    # Group: Data Processing
    proc_group = parser.add_argument_group('Data Processing')
    proc_group.add_argument('-n', '--limit', type=int, default=0,
                        help='Only process the first N cards.')
    proc_group.add_argument('-s', '--stable', action='store_true',
                        help='Keep the original order of cards from the input (do not shuffle).')
    proc_group.add_argument('--seed', type=int,
                        help='Seed for the random number generator (Default: 1371367).')
    proc_group.add_argument('--sample', type=int, default=0,
                        help='Pick N random cards from the input (shorthand for --limit N). Shuffling is enabled unless --stable is used.')
    proc_group.add_argument('--sort', choices=['name', 'color', 'type', 'cmc', 'rarity', 'power', 'toughness', 'loyalty', 'set', 'pack'],
                        help='Sort cards by a specific criterion (enables --stable).')
    proc_group.add_argument('--grep', action='append',
                        help='Only include cards matching a search pattern (checks name, type, and text). Use multiple times for AND logic.')
    proc_group.add_argument('--grep-name', action='append',
                        help='Only include cards whose name matches a search pattern.')
    proc_group.add_argument('--grep-type', action='append',
                        help='Only include cards whose typeline matches a search pattern.')
    proc_group.add_argument('--grep-text', action='append',
                        help='Only include cards whose rules text matches a search pattern.')
    proc_group.add_argument('--grep-cost', action='append',
                        help='Only include cards whose mana cost matches a search pattern.')
    proc_group.add_argument('--grep-pt', action='append',
                        help='Only include cards whose power/toughness matches a search pattern.')
    proc_group.add_argument('--grep-loyalty', action='append',
                        help='Only include cards whose loyalty/defense matches a search pattern.')
    proc_group.add_argument('--vgrep', '--exclude', action='append',
                        help='Exclude cards matching a search pattern (checks name, type, and text). Use multiple times for OR logic.')
    proc_group.add_argument('--exclude-name', action='append',
                        help='Exclude cards whose name matches a search pattern.')
    proc_group.add_argument('--exclude-type', action='append',
                        help='Exclude cards whose typeline matches a search pattern.')
    proc_group.add_argument('--exclude-text', action='append',
                        help='Exclude cards whose rules text matches a search pattern.')
    proc_group.add_argument('--exclude-cost', action='append',
                        help='Exclude cards whose mana cost matches a search pattern.')
    proc_group.add_argument('--exclude-pt', action='append',
                        help='Exclude cards whose power/toughness matches a search pattern.')
    proc_group.add_argument('--exclude-loyalty', action='append',
                        help='Exclude cards whose loyalty/defense matches a search pattern.')
    proc_group.add_argument('--set', action='append',
                        help='Only include cards from specific sets (e.g., MOM, MRD). Supports multiple sets (OR logic).')
    proc_group.add_argument('--rarity', action='append',
                        help="Only include cards of specific rarities. Supports full names or shorthands (O, N, A, Y, I, L). Supports multiple rarities.")
    proc_group.add_argument('--colors', action='append',
                        help="Only include cards of specific colors (W, U, B, R, G, C/A). Supports multiple colors.")
    proc_group.add_argument('--cmc', action='append',
                        help='Only include cards with specific CMC values. Supports inequalities and ranges.')
    proc_group.add_argument('--pow', '--power', action='append', dest='pow',
                        help='Only include cards with specific Power values. Supports inequalities and ranges.')
    proc_group.add_argument('--tou', '--toughness', action='append', dest='tou',
                        help='Only include cards with specific Toughness values. Supports inequalities and ranges.')
    proc_group.add_argument('--loy', '--loyalty', '--defense', action='append', dest='loy',
                        help='Only include cards with specific Loyalty or Defense values. Supports inequalities and ranges.')
    proc_group.add_argument('--mechanic', action='append',
                        help='Only include cards with specific mechanical features or keyword abilities. Supports multiple values.')
    proc_group.add_argument('--deck-filter', '--decklist-filter', dest='deck',
                        help='Filter cards using a standard MTG decklist file.')
    proc_group.add_argument('--booster', type=int, default=0,
                        help='Simulate opening N booster packs. Distribution: 10 Common, 3 Uncommon, 1 Rare/Mythic, 1 Basic Land. Shuffles by default.')
    proc_group.add_argument('--box', type=int, default=0,
                        help='Simulate opening N booster boxes (36 packs each). Shuffles by default.')

    # Group: Logging & Debugging
    log_group = parser.add_argument_group('Logging & Debugging')
    log_group.add_argument('-v', '--verbose', action='store_true', help='Enable detailed status messages.')
    log_group.add_argument('-q', '--quiet', action='store_true', help='Suppress the progress bar.')

    # Legacy flags for backward compatibility
    parser.add_argument('--shuffle', action='store_true', default=True, help=argparse.SUPPRESS)
    parser.add_argument('--no-shuffle', dest='shuffle', action='store_false', help=argparse.SUPPRESS)

    args = parser.parse_args()

    # Handle --sample
    if args.sample > 0:
        args.limit = args.sample

    if args.sort:
        args.stable = True

    if len(args.outputs) != len(args.ratios):
        print("Error: The number of outputs must match the number of ratios.", file=sys.stderr)
        sys.exit(1)

    if abs(sum(args.ratios) - 1.0) > 1e-6:
        if not args.quiet:
            print(f"Warning: Ratios sum to {sum(args.ratios):.4f}, normalizing to 1.0.", file=sys.stderr)
        total = sum(args.ratios)
        args.ratios = [r / total for r in args.ratios]

    # Load cards
    if not args.quiet:
        print(f"Loading cards from {args.infile}...", file=sys.stderr)

    # mtg_open_file handles format detection and comprehensive filtering
    cards = jdecode.mtg_open_file(args.infile, verbose=args.verbose,
                                  linetrans=not args.nolinetrans,
                                  grep=args.grep, vgrep=args.vgrep,
                                  grep_name=args.grep_name, vgrep_name=args.exclude_name,
                                  grep_types=args.grep_type, vgrep_types=args.exclude_type,
                                  grep_text=args.grep_text, vgrep_text=args.exclude_text,
                                  grep_cost=args.grep_cost, vgrep_cost=args.exclude_cost,
                                  grep_pt=args.grep_pt, vgrep_pt=args.exclude_pt,
                                  grep_loyalty=args.grep_loyalty, vgrep_loyalty=args.exclude_loyalty,
                                  sets=args.set, rarities=args.rarity, colors=args.colors, cmcs=args.cmc,
                                  pows=args.pow, tous=args.tou, loys=args.loy,
                                  mechanics=args.mechanic,
                                  shuffle=not args.stable, seed=args.seed if args.seed is not None else 1371367,
                                  decklist_file=args.deck, booster=args.booster, box=args.box)

    if args.sort:
        cards = sortlib.sort_cards(cards, args.sort, quiet=args.quiet)

    if args.limit > 0:
        cards = cards[:args.limit]

    total_cards = len(cards)
    if not args.quiet:
        print(f"Total cards matching filters: {total_cards}", file=sys.stderr)

    if total_cards == 0:
        print("Error: No cards matched filters.", file=sys.stderr)
        sys.exit(1)

    # Calculate split indices
    indices = []
    current = 0
    for i, ratio in enumerate(args.ratios):
        if i == len(args.ratios) - 1:
            # Last split gets the remainder to ensure we use all cards
            indices.append((current, total_cards))
        else:
            count = int(round(ratio * total_cards))
            indices.append((current, current + count))
            current += count

    # Write splits
    for i, (start, end) in enumerate(indices):
        outfile = args.outputs[i]
        split_cards = cards[start:end]

        if not args.quiet:
            print(f"Writing {len(split_cards)} cards to {outfile} (format: {args.format})...", file=sys.stderr)

        with open(outfile, 'w', encoding='utf8') as f:
            if args.format == 'json':
                json_data = [c.to_dict() for c in split_cards]
                json.dump(json_data, f, indent=2)
            elif args.format == 'jsonl':
                for c in split_cards:
                    f.write(json.dumps(c.to_dict()) + '\n')
            elif args.format == 'csv':
                fieldnames = ['name', 'mana_cost', 'type', 'subtypes', 'text', 'power', 'toughness', 'loyalty', 'rarity']
                writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator='\n')
                writer.writeheader()
                for c in split_cards:
                    d = c.to_dict()
                    row = {
                        'name': d.get('name', ''),
                        'mana_cost': d.get('manaCost', ''),
                        'type': ' '.join(d.get('supertypes', []) + d.get('types', [])),
                        'subtypes': ' '.join(d.get('subtypes', [])),
                        'text': d.get('text', ''),
                        'power': d.get('power', d.get('pt', '') if '/' not in d.get('pt', '') else ''),
                        'toughness': d.get('toughness', ''),
                        'loyalty': d.get('loyalty', d.get('defense', '')),
                        'rarity': d.get('rarity', ''),
                    }
                    writer.writerow(row)
            else: # text (encoded)
                # determine the encoding parameters
                fmt_ordered = cardlib.fmt_ordered_default
                fmt_labeled = None if args.nolabel else cardlib.fmt_labeled_default
                fieldsep = utils.fieldsep
                randomize_fields = False
                randomize_mana = False
                initial_sep = True
                final_sep = True

                ENCODING_CONFIG = {
                    'std': {},
                    'named': {'fmt_ordered': cardlib.fmt_ordered_named},
                    'noname': {'fmt_ordered': cardlib.fmt_ordered_noname},
                    'rfields': {'randomize_fields': True, 'final_sep': False},
                    'old': {'fmt_ordered': cardlib.fmt_ordered_old},
                    'norarity': {'fmt_ordered': cardlib.fmt_ordered_norarity},
                    'vec': {},
                    'custom': {},
                }

                config = ENCODING_CONFIG.get(args.encoding, {})
                fmt_ordered = config.get('fmt_ordered', fmt_ordered)
                randomize_fields = config.get('randomize_fields', randomize_fields)
                final_sep = config.get('final_sep', final_sep)

                for c in split_cards:
                    if args.encoding == 'vec':
                        f.write(c.vectorize() + '\n\n')
                    else:
                        f.write(c.encode(fmt_ordered = fmt_ordered,
                                         fmt_labeled = fmt_labeled,
                                         fieldsep = fieldsep,
                                         randomize_fields = randomize_fields,
                                         randomize_mana = randomize_mana,
                                         initial_sep = initial_sep,
                                         final_sep = final_sep)
                                + utils.cardsep)

    if not args.quiet:
        print("Dataset split successfully.", file=sys.stderr)

if __name__ == '__main__':
    main()
