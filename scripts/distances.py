#!/usr/bin/env python3
import sys
import os
import json
import csv

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)
import jdecode
from namediff import Namediff
from cbow import CBOW

default_infile = os.path.join(libdir, '../data/output.txt')

def main(fname, oname, verbose = True, parallel = True, dry_run = False, use_json = False, use_csv = False):
    if not use_json and not use_csv and oname:
        if oname.endswith('.json'):
            use_json = True
        elif oname.endswith('.csv'):
            use_csv = True
    if fname != '-' and not os.path.exists(fname):
        print(f"Error: File not found: {fname}", file=sys.stderr)
        sys.exit(1)

    cards = jdecode.mtg_open_file(fname, verbose=verbose)

    if dry_run:
        print(f"Dry Run Summary: {len(cards)} card(s) loaded from {fname}.")
        print(f"Output File: {oname if oname else 'None'}")
        print(f"Parallel Processing: {'Enabled' if parallel else 'Disabled'}")
        sample_names = [getattr(c, 'name', str(c)) for c in cards[:10]]
        if sample_names:
            print("Sample Card Preview:")
            for name in sample_names:
                print(f"  - {name}")
        return

    # this could reasonably be some separate function
    # might make sense to merge cbow and namediff and have this be the main interface
    namediff = Namediff()
    cbow = CBOW()

    if verbose:
        print('Computing nearest names...')
    if parallel:
        nearest_names = namediff.nearest_par([c.name for c in cards], n=1)
    else:
        nearest_names = [namediff.nearest(c.name, n=1) for c in cards]

    if verbose:
        print('Computing nearest cards...')
    if parallel:
        nearest_cards = cbow.nearest_par(cards, n=1)
    else:
        nearest_cards = [cbow.nearest(c, n=1) for c in cards]

    for i in range(0, len(cards)):
        cards[i].nearest_names = nearest_names[i]
        cards[i].nearest_cards = nearest_cards[i]

    # # unfortunately this takes ~30 hours on 8 cores for a 10MB dump
    # if verbose:
    #     print 'Computing nearest encodings by text edit distance...'
    # if parallel:
    #     nearest_cards_text = namediff.nearest_card_par(cards, n=1)
    # else:
    #     nearest_cards_text = [namediff.nearest_card(c, n=1) for c in cards]

    if verbose:
        print('...Done.')

    if use_json:
        records = []
        for i, card in enumerate(cards):
            ndist, _ = card.nearest_names[0]
            cdist, _ = card.nearest_cards[0]
            records.append({
                'index': i,
                'name': card.name,
                'nearest_name_similarity': float(ndist),
                'nearest_card_similarity': float(cdist)
            })
        if oname and oname != '-':
            with open(oname, 'w', encoding='utf-8') as ofile:
                json.dump(records, ofile, indent=2)
                ofile.write('\n')
        else:
            json.dump(records, sys.stdout, indent=2)
            sys.stdout.write('\n')
        return

    if use_csv:
        output_f = sys.stdout
        if oname and oname != '-':
            output_f = open(oname, 'w', encoding='utf-8', newline='')
        try:
            writer = csv.writer(output_f)
            writer.writerow(['index', 'name', 'nearest_name_similarity', 'nearest_card_similarity'])
            for i, card in enumerate(cards):
                ndist, _ = card.nearest_names[0]
                cdist, _ = card.nearest_cards[0]
                writer.writerow([i, card.name, ndist, cdist])
        finally:
            if oname and oname != '-' and output_f:
                output_f.close()
        return

    # write to a file to store the data, this is a terribly long computation
    # we could also just store this same info in the cards themselves as more fields...
    sep = '|'
    output_f = sys.stdout
    if oname and oname != '-':
        output_f = open(oname, 'w', encoding='utf-8')

    try:
        for i in range(0, len(cards)):
            card = cards[i]
            ostr = str(i) + sep + card.name + sep
            ndist, _ = card.nearest_names[0]
            ostr += str(ndist) + sep
            cdist, _ = card.nearest_cards[0]
            ostr += str(cdist) + '\n'
            # tdist, _ = nearest_cards_text[i][0]
            # ostr += str(tdist) + '\n'
            output_f.write(ostr)
    finally:
        if oname and oname != '-' and output_f:
            output_f.close()

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description="Calculate the semantic and name distance between generated cards and the official dataset.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Analyze distance stats with standard inputs and outputs
  python3 scripts/distances.py data/output.txt distances.txt

  # Run calculations using default output file (distances.txt)
  python3 scripts/distances.py data/output.txt

  # Export distance calculations to JSON or CSV format
  python3 scripts/distances.py data/output.txt distances.json
  python3 scripts/distances.py data/output.txt distances.csv --csv

  # Enable parallel processing on all CPU cores
  python3 scripts/distances.py data/output.txt distances.txt --parallel

  # Preview card count and distance calculation settings without running
  python3 scripts/distances.py data/output.txt --dry-run
"""
    )

    # Group: Input / Output
    io_group = parser.add_argument_group('Input / Output')
    io_group.add_argument('infile', nargs='?', default=default_infile,
                        help='The card dataset to analyze (JSON, CSV, or encoded text). Defaults to data/output.txt.')
    io_group.add_argument('outfile', nargs='?', default='distances.txt',
                        help='Path to save the distance data (default: distances.txt). Used as input for scripts/sum.py.')

    # Group: Output Format
    fmt_group = parser.add_argument_group('Output Format')
    fmt_group.add_argument('-j', '--json', action='store_true',
                        help='Export distance calculation results in structured JSON format (Auto-detected if outfile ends with .json).')
    fmt_group.add_argument('--csv', action='store_true',
                        help='Export distance calculation results in CSV format (Auto-detected if outfile ends with .csv).')

    # Group: Processing Options
    proc_group = parser.add_argument_group('Processing Options')
    proc_group.add_argument('-p', '--parallel', action='store_true',
                        help='Run calculations in parallel on all CPU cores for faster processing.')
    proc_group.add_argument('-d', '--dry-run', '--preview', dest='dry_run', action='store_true',
                        help='Print a summary of distance analysis parameters (total cards loaded, parallel status, output destination, and sample card preview) without running calculations or writing output files.')
    proc_group.add_argument('-v', '--verbose', action='store_true',
                        help='Enable detailed status messages.')

    args = parser.parse_args()

    if args.infile == default_infile and not os.path.exists(default_infile) and sys.stdin.isatty() and not args.dry_run:
        parser.print_help()
        sys.exit(1)

    main(args.infile, args.outfile, verbose=args.verbose, parallel=args.parallel, dry_run=args.dry_run, use_json=args.json, use_csv=args.csv)
    sys.exit(0)
