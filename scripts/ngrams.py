#!/usr/bin/env python3
import sys
import os
import pickle
import argparse

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)
import jdecode
from nltk.lm.preprocessing import padded_everygram_pipeline
from nltk.lm import MLE
from nltk.util import ngrams as nltk_ngrams

class NgramModelWrapper:
    def __init__(self, n, lang):
        self.n = n
        train, vocab = padded_everygram_pipeline(n, lang)
        self.lm = MLE(n)
        self.lm.fit(train, vocab)
    
    def perplexity(self, text):
        # text is a list of strings
        # Ngram model perplexity expects a list of ngrams
        ngs = list(nltk_ngrams(text, self.n))
        if not ngs:
            return 0.0
        return self.lm.perplexity(ngs)

def update_ngrams(lines, gramdict, grams):
    for line in lines:
        for i in range(0, len(line) - (grams - 1)):
            ngram = ' '.join([line[i + j] for j in range(0, grams)])
            if ngram in gramdict:
                gramdict[ngram] += 1
            else:
                gramdict[ngram] = 1

def describe_bins(gramdict, bins):
    bins = sorted(bins)
    counts = [0 for _ in range(0, len(bins) + 1)]

    for ngram in gramdict:
        for i in range(0, len(bins) + 1):
            if i < len(bins):
                if gramdict[ngram] <= bins[i]:
                    counts[i] += 1
                    break
            else:
                # didn't fit into any of the smaller bins, stick in on the end
                counts[-1] += 1
    
    lines = []
    for i in range(0, len(counts)):
        if counts[i] > 0:
            lines.append('  ' + (str(bins[i]) if i < len(bins) else str(bins[-1]) + '+')
                         + ': ' + str(counts[i]))
    return lines


def extract_language(cards, separate_lines=True):
    if separate_lines:
        lang = [line.vectorize() for card in cards for line in card.text_lines]
    else:
        lang = [card.text.vectorize() for card in cards]
    return [s.split() for s in lang]


def build_ngram_model(cards, n, separate_lines=True, verbose=False):
    if verbose:
        print(('generating ' + str(n) + '-gram model'))
    lang = extract_language(cards, separate_lines=separate_lines)
    if verbose:
        print(('found ' + str(len(lang)) + ' sentences'))
    lm = NgramModelWrapper(n, lang)
    return lm

def main(fname=None, oname=None, gmin=2, gmax=8, nltk=False, sep=False, verbose=False, dry_run=False):
    gmin = int(gmin)
    gmax = int(gmax)

    # Determine default dataset if fname is omitted
    script_dir = os.path.dirname(os.path.realpath(__file__))
    default_base = 'data/AllPrintings.json'
    if not os.path.exists(default_base):
        rel_data = os.path.join(script_dir, '../data/AllPrintings.json')
        if os.path.exists(rel_data):
            default_base = rel_data

    if fname is None:
        if os.path.exists(default_base):
            fname = default_base
        elif sys.stdin.isatty():
            print("Error: Input file required.", file=sys.stderr)
            sys.exit(1)
        else:
            fname = '-'
    elif oname is None:
        if not os.path.exists(fname) and os.path.exists(default_base):
            oname = fname
            fname = default_base

    if not dry_run and not oname:
        if sys.stdin.isatty() or sys.stdout.isatty():
            dry_run = True
            print("Notice: No output file specified. Running in dry-run preview mode.", file=sys.stderr)
            sys.stderr.flush()
        else:
            print("Error: Output file required unless --dry-run is specified.", file=sys.stderr)
            sys.exit(1)

    cards = jdecode.mtg_open_file(fname, verbose=verbose)

    if dry_run:
        print(f"Dry Run Summary: Evaluated {len(cards)} card(s).")
        total_lines = sum(len(getattr(c, 'text_lines_words', [])) for c in cards)
        print(f"Total Text Lines: {total_lines}")
        if nltk:
            n = gmin
            lang = extract_language(cards, separate_lines=sep)
            print(f"NLTK Model Settings: n={n}, separate_lines={sep}, total sentences={len(lang)}")
        else:
            if gmin < 2 or gmax < gmin:
                print('invalid gram sizes: ' + str(gmin) + '-' + str(gmax))
                sys.exit(1)

            bins = [1, 2, 3, 10, 30, 100, 300, 1000]
            print(f"N-Gram Range: {gmin}-gram to {gmax}-gram")
            for grams in range(gmin, gmax + 1):
                gramdict = {}
                for card in cards:
                    update_ngrams(getattr(card, 'text_lines_words', []), gramdict, grams)
                print(f"  {grams}-gram: {len(gramdict)} unique n-gram(s)")
                bin_lines = describe_bins(gramdict, bins)
                for bl in bin_lines:
                    print(f"  {bl}")
                top_grams = sorted(gramdict, key=lambda x: gramdict[x], reverse=True)[:5]
                top_str = ", ".join(f"'{g}': {gramdict[g]}" for g in top_grams)
                print(f"    Top n-grams: {top_str if top_str else 'None'}")
        return

    if nltk:
        n = gmin
        lm = build_ngram_model(cards, n, separate_lines=sep, verbose=verbose)
        if verbose:
            teststr = 'when @ enters the battlefield'
            print(('litmus test: perplexity of ' + repr(teststr)))
            print(('  ' + str(lm.perplexity(teststr.split()))))
        if verbose:
            print(('pickling module to ' + oname))
        with open(oname, 'wb') as f:
            pickle.dump(lm, f)

    else:
        bins = [1, 2, 3, 10, 30, 100, 300, 1000]
        if gmin < 2 or gmax < gmin:
            print('invalid gram sizes: ' + str(gmin) + '-' + str(gmax))
            sys.exit(1)

        for grams in range(gmin, gmax + 1):
            if verbose:
                print('generating ' + str(grams) + '-grams...')
            gramdict = {}
            for card in cards:
                update_ngrams(getattr(card, 'text_lines_words', []), gramdict, grams)

            oname_full = oname + '.' + str(grams) + 'g'
            if verbose:
                print(('  writing ' + str(len(gramdict)) + ' unique ' + str(grams)
                       + '-grams to ' + oname_full))
                bin_lines = describe_bins(gramdict, bins)
                for bl in bin_lines:
                    print(bl)

            with open(oname_full, 'w', encoding='utf-8') as f:
                for ngram in sorted(gramdict,
                                    key=lambda x: gramdict[x],
                                    reverse = True):
                    f.write(ngram + ': ' + str(gramdict[ngram]) + '\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='ngrams.py',
        description="Extract n-grams or build an NLTK language model from encoded cards or MTG card data.",
        epilog='''
Example Usage:
  # Generate n-grams for 2-gram to 8-gram
  python3 scripts/ngrams.py testdata/uthros.json my_ngrams

  # Preview n-gram statistics without writing output files (dry run mode)
  python3 scripts/ngrams.py testdata/uthros.json --dry-run

  # Build an NLTK model pickled to file
  python3 scripts/ngrams.py testdata/uthros.json model.pkl -nltk -min 3
''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Input / Output
    io_group = parser.add_argument_group('Input / Output Options')
    io_group.add_argument('infile', nargs='?', default=None,
                        help='Encoded card file or JSON corpus to process. Defaults to data/AllPrintings.json if omitted.')
    io_group.add_argument('outfile', nargs='?', default=None,
                        help='Base name of output file (e.g. outputs ending in .2g, .3g etc. will be produced). Optional if --dry-run is specified.')
    
    # Processing & Debugging
    proc_group = parser.add_argument_group('Processing Options')
    proc_group.add_argument('-p', '--preview', '--dry-run', dest='dry_run', action='store_true',
                        help='Print a summary of n-gram statistics (card count, line count, unique n-grams per size, bin breakdown, and top n-grams) to standard output without creating or writing output files.')
    proc_group.add_argument('-min', '--min', action='store', default='2',
                        help='Minimum gram size to compute (Default: 2).')
    proc_group.add_argument('-max', '--max', action='store', default='8',
                        help='Maximum gram size to compute (Default: 8).')
    proc_group.add_argument('-nltk', '--nltk', action='store_true',
                        help='Use NLTK model (MLE) with n = min.')
    proc_group.add_argument('-s', '--separate', action='store_true',
                        help='Separate card text into lines when constructing NLTK model.')
    proc_group.add_argument('-v', '--verbose', action='store_true',
                        help='Verbose output.')

    args = parser.parse_args()
    main(args.infile, args.outfile, gmin=args.min, gmax=args.max, nltk=args.nltk,
         sep=args.separate, verbose=args.verbose, dry_run=args.dry_run)
    sys.exit(0)
