#!/usr/bin/env python3
import sys
import os
import json

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)
import utils
import jdecode
import transforms

def check_lines(fname):
    cards = jdecode.mtg_open_file(fname, verbose=True, linetrans=True)

    prelines = set()
    keylines = set()
    mainlines = set()
    costlines = set()
    postlines = set()

    known = ['enchant ', 'equip', 'countertype', 'multikicker', 'kicker',
             'suspend', 'echo', 'awaken', 'bestow', 'buyback',
             'cumulative', 'dash', 'entwine', 'evoke', 'fortify',
             'flashback', 'madness', 'morph', 'megamorph', 'miracle', 'ninjutsu',
             'overload', 'prowl', 'recover', 'reinforce', 'replicate', 'scavenge',
             'splice', 'surge', 'unearth', 'transfigure', 'transmute',
    ]
    known = []

    for card in cards:
        prel, keyl, mainl, costl, postl = transforms.separate_lines(card.text.encode(randomize=False))
        if card.bside:
            prel2, keyl2, mainl2, costl2, postl2 = transforms.separate_lines(card.bside.text.encode(randomize=False))
            prel += prel2
            keyl += keyl2
            mainl += mainl2
            costl += costl2
            postl += postl2

        for line in prel:
            if line.strip() == '':
                print((card.name, card.text.text))
            if any(line.startswith(s) for s in known):
                line = 'known'
            prelines.add(line)
        for line in postl:
            if line.strip() == '':
                print((card.name, card.text.text))
            if any(line.startswith(s) for s in known):
                line = 'known'
            postlines.add(line)
        for line in keyl:
            if line.strip() == '':
                print((card.name, card.text.text))
            if any(line.startswith(s) for s in known):
                line = 'known'
            keylines.add(line)
        for line in mainl:
            if line.strip() == '':
                print((card.name, card.text.text))
            # if any(line.startswith(s) for s in known):
            #     line = 'known'
            mainlines.add(line)
        for line in costl:
            if line.strip() == '':
                print((card.name, card.text.text))
            # if any(line.startswith(s) for s in known) or 'cycling' in line or 'monstrosity' in line:
            #     line = 'known'
            costlines.add(line)

    print(('prel: {:d}, keyl: {:d}, mainl: {:d}, postl {:d}'
           .format(len(prelines), len(keylines), len(mainlines), len(postlines))))

    print('\nprelines')
    for line in sorted(prelines):
        print(line)

    print('\npostlines')
    for line in sorted(postlines):
        print(line)

    print('\ncostlines')
    for line in sorted(costlines):
        print(line)

    print('\nkeylines')
    for line in sorted(keylines):
        print(line)

    print('\nmainlines')
    for line in sorted(mainlines):
        #if any(s in line for s in ['champion', 'devour', 'tribute']):
        print(line)

def check_vocab(fname):
    cards = jdecode.mtg_open_file(fname, verbose=True, linetrans=True)

    vocab = {}
    for card in cards:
        words = card.text.vectorize().split()
        if card.bside:
            words += card.bside.text.vectorize().split()
        for word in words:
            if word not in vocab:
                vocab[word] = 1
            else:
                vocab[word] += 1

    for word in sorted(vocab, key=lambda x: vocab[x], reverse=True):
        print(('{:8d} : {:s}'.format(vocab[word], word)))

    n = 3

    for card in cards:
        words = card.text.vectorize().split()
        if card.bside:
            words += card.bside.text.vectorize().split()
        for word in words:
            if vocab[word] <= n:
            #if 'name' in word:
                print(('\n{:8d} : {:s}'.format(vocab[word], word)))
                print((card.encode()))
                break

def check_characters(fname, vname):
    cards = jdecode.mtg_open_file(fname, verbose=True, linetrans=True)

    tokens = {c for c in utils.cardsep}
    for card in cards:
        for c in card.encode():
            tokens.add(c)

    token_to_idx = {tok:i+1 for i, tok in enumerate(sorted(tokens))}
    idx_to_token = {i+1:tok for i, tok in enumerate(sorted(tokens))}

    print(('Vocabulary: ({:d} symbols)'.format(len(token_to_idx))))
    for token in sorted(token_to_idx):
        print(('{:8s} : {:4d}'.format(repr(token), token_to_idx[token])))

    # compliant with torch-rnn
    if vname:
        json_data = {'token_to_idx': token_to_idx,
                     'idx_to_token': idx_to_token}
        print(('writing vocabulary to {:s}'.format(vname)))
        with open(vname, 'w') as f:
            json.dump(json_data, f)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description="Inspect and verify character, vocabulary, and line-structure consistency in card data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Check line separation behavior
  python3 scripts/sanity.py data/output.txt -lines

  # Display vocabulary counts from card text
  python3 scripts/sanity.py data/output.txt -vocab

  # Inspect character encoding vocabulary and save to JSON
  python3 scripts/sanity.py data/output.txt -chars --vocab_name vocab.json

  # Dry-run preview mode without processing or saving vocabulary JSON
  python3 scripts/sanity.py data/output.txt -chars --vocab_name vocab.json -p
"""
    )

    io_group = parser.add_argument_group('Input / Output Options')
    io_group.add_argument('infile', nargs='?', default=os.path.join(libdir, '../data/output.txt'),
                        help='Input card data file (encoded text or JSON dataset). Defaults to data/output.txt.')
    io_group.add_argument('--vocab_name', default=None,
                        help='Path to save the character vocabulary as a JSON file.')

    check_group = parser.add_argument_group('Sanity Check Options')
    check_group.add_argument('-lines', action='store_true',
                        help='Inspect and print line separation categories for card rules text.')
    check_group.add_argument('-vocab', action='store_true',
                        help='Count word frequencies in encoded card text and display rare words.')
    check_group.add_argument('-chars', action='store_true',
                        help='Extract and display all unique characters used in card encoding.')

    proc_group = parser.add_argument_group('Processing Options')
    proc_group.add_argument('-p', '--preview', '--dry-run', dest='dry_run', action='store_true',
                        help='Print a summary of active sanity checks, target files, and card dataset statistics without running calculations or writing files.')

    args = parser.parse_args()

    if not (args.lines or args.vocab or args.chars):
        parser.print_help(sys.stderr)
        sys.exit(1)

    if args.dry_run:
        cards = jdecode.mtg_open_file(args.infile, verbose=False, linetrans=True)
        active_modes = []
        if args.lines:
            active_modes.append("lines")
        if args.vocab:
            active_modes.append("vocab")
        if args.chars:
            active_modes.append("chars")
        print("Dry Run Summary:")
        print(f"  Input File: {args.infile} ({len(cards)} card(s) loaded)")
        print(f"  Active Checks: {', '.join(active_modes)}")
        print(f"  Vocab Output Target: {args.vocab_name if args.vocab_name else 'None'}")
        sample_names = [card.name for card in cards[:10] if hasattr(card, 'name') and card.name]
        if sample_names:
            print(f"  Sample Cards Preview: {', '.join(sample_names)}")
        sys.exit(0)

    if args.lines:
        check_lines(args.infile)
    if args.vocab:
        check_vocab(args.infile)
    if args.chars:
        check_characters(args.infile, args.vocab_name)

    sys.exit(0)
