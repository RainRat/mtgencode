#!/usr/bin/env python3
import sys
import os
import json
import csv
from collections import OrderedDict

# scipy is kinda necessary
import scipy
import scipy.stats
import numpy as np
import math

def mean_nonan(l):
    filtered = [x for x in l if not math.isnan(x)]
    return np.mean(filtered) if filtered else 0.0

def gmean_nonzero(l):
    filtered = [x for x in l if x != 0 and not math.isnan(x)]
    if not filtered:
        return 0.0
    return scipy.stats.gmean(filtered)

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)
scriptsdir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(scriptsdir)
datadir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../data')
import jdecode

import mtg_validate
import ngrams

def print_statistics(stats, ident = 0, file = None):
    if file is None:
        file = sys.stdout
    for k in stats:
        if isinstance(stats[k], OrderedDict):
            print((' ' * ident + str(k) + ':'), file=file)
            print_statistics(stats[k], ident=ident + 2, file=file)
        elif isinstance(stats[k], dict):
            print((' ' * ident + str(k) + ': <dict with ' +
                   str(len(stats[k])) + ' entries>'), file=file)
        elif isinstance(stats[k], list):
            print((' ' * ident + str(k) + ': <list with ' +
                   str(len(stats[k])) + ' entries>'), file=file)
        else:
            print((' ' * ident + str(k) + ': ' + str(stats[k])), file=file)

def sanitize_value(val):
    if isinstance(val, (float, np.floating)):
        if math.isnan(val) or math.isinf(val):
            return None
        return float(val)
    if isinstance(val, (int, np.integer)):
        return int(val)
    if isinstance(val, (list, tuple)):
        return [sanitize_value(v) for v in val]
    if isinstance(val, (dict, OrderedDict)):
        return {k: sanitize_value(v) for k, v in val.items()}
    return val

def stats_to_dict(stats):
    res = {}
    for k, v in stats.items():
        if k == 'cards':
            res['card_count'] = len(v) if isinstance(v, list) else 0
        else:
            res[k] = sanitize_value(v)
    return res

def export_csv_stats(stats, file):
    writer = csv.writer(file)
    writer.writerow(['Category', 'Metric', 'Value'])

    if 'cards' in stats:
        writer.writerow(['summary', 'card_count', len(stats['cards'])])

    for cat_key in ['cp', 'props', 'dists', 'ngram']:
        if cat_key not in stats or not stats[cat_key]:
            continue
        cat_data = stats[cat_key]
        if isinstance(cat_data, (dict, OrderedDict)):
            for metric, val in cat_data.items():
                if isinstance(val, (dict, OrderedDict)):
                    for sub_m, sub_v in val.items():
                        writer.writerow([f"{cat_key}.{metric}", sub_m, sanitize_value(sub_v)])
                elif isinstance(val, list):
                    continue
                else:
                    writer.writerow([cat_key, metric, sanitize_value(val)])

def get_statistics(fname, lm = None, sep = False, verbose=False):
    stats = OrderedDict()
    cards = jdecode.mtg_open_file(fname, verbose=verbose)
    stats['cards'] = cards

    # unpack the name of the checkpoint - terrible and hacky
    try:
        final_name = os.path.basename(fname)
        halves = final_name.split('_epoch')
        cp_name = halves[0]
        cp_info = halves[1][:-4]
        info_halves = cp_info.split('_')
        cp_epoch = float(info_halves[0])
        fragments = info_halves[1].split('.')
        cp_vloss = float('.'.join(fragments[:2]))
        cp_temp = float('.'.join(fragments[-2:]))
        cp_ident = '.'.join(fragments[2:-2])
        stats['cp'] = OrderedDict([('name', cp_name),
                                   ('epoch', cp_epoch),
                                   ('vloss', cp_vloss),
                                   ('temp', cp_temp),
                                   ('ident', cp_ident)])
    except (IndexError, ValueError):
        pass

    # validate
    ((total_all, total_good, total_bad, total_uncovered), 
         values) = mtg_validate.process_props(cards)
    
    for k in values:
        (total, good, bad) = values[k]
        values[k] = OrderedDict([('total', total), ('good', good), ('bad', bad)])

    stats['props'] = values
    stats['props']['overall'] = OrderedDict([('total', total_all), 
                                             ('good', total_good), 
                                             ('bad', total_bad), 
                                             ('uncovered', total_uncovered)])

    # distances
    distfname = fname + '.dist'
    if os.path.isfile(distfname):
        name_dupes = 0
        card_dupes = 0
        with open(distfname, 'rt') as f:
            distlines = f.read().split('\n')
        dists = OrderedDict([('name', []), ('cbow', [])])
        for line in distlines:
            fields = line.split('|')
            if len(fields) < 4:
                continue
            idx = int(fields[0])
            name = str(fields[1])
            ndist = float(fields[2])
            cdist = float(fields[3])
            dists['name'] += [ndist]
            dists['cbow'] += [cdist]
            if ndist == 1.0:
                name_dupes += 1
            if cdist == 1.0:
                card_dupes += 1

        dists['name_mean'] = mean_nonan(dists['name'])
        dists['cbow_mean'] = mean_nonan(dists['cbow'])
        dists['name_geomean'] = gmean_nonzero(dists['name'])
        dists['cbow_geomean'] = gmean_nonzero(dists['cbow'])
        stats['dists'] = dists
        
    # n-grams
    if lm is not None:
        ngram = OrderedDict([('perp', []), ('perp_per', []), 
                             ('perp_max', []), ('perp_per_max', [])])
        for card in cards:
            if len(card.text.text) == 0:
                perp = 0.0
                perp_per = 0.0
            elif sep:
                vtexts = [line.vectorize().split() for line in card.text_lines 
                          if len(line.vectorize().split()) > 0]
                perps = [lm.perplexity(vtext) for vtext in vtexts]
                perps_per = [perps[i] / float(len(vtexts[i])) for i in range(0, len(vtexts))]
                perp = gmean_nonzero(perps)
                perp_per = gmean_nonzero(perps_per)
                perp_max = max(perps)
                perp_per_max = max(perps_per)
            else:
                vtext = card.text.vectorize().split()
                perp = lm.perplexity(vtext)
                perp_per = perp / float(len(vtext))
                perp_max = perp
                perp_per_max = perp_per

            ngram['perp'] += [perp]
            ngram['perp_per'] += [perp_per]
            ngram['perp_max'] += [perp_max]
            ngram['perp_per_max'] += [perp_per_max]

        ngram['perp_mean'] = mean_nonan(ngram['perp'])
        ngram['perp_per_mean'] = mean_nonan(ngram['perp_per'])
        ngram['perp_geomean'] = gmean_nonzero(ngram['perp'])
        ngram['perp_per_geomean'] = gmean_nonzero(ngram['perp_per'])
        stats['ngram'] = ngram

    return stats


def main(infile = None, outfile = None, json_fmt = False, csv_fmt = False, dry_run = False, verbose = False):
    if isinstance(outfile, bool) and verbose is False:
        verbose = outfile
        outfile = None

    default_infile = os.path.join(datadir, 'output.txt')
    if not infile:
        if os.path.exists(default_infile):
            infile = default_infile
        else:
            infile = os.path.join(datadir, 'AllPrintings.json')

    if outfile:
        if outfile.endswith('.json'):
            json_fmt = True
        elif outfile.endswith('.csv'):
            csv_fmt = True

    if dry_run:
        file_exists = os.path.exists(infile)
        dest_str = outfile if outfile else 'Console (sys.stdout)'
        fmt_str = 'JSON' if json_fmt else ('CSV' if csv_fmt else 'Standard Text')
        print(f"Dry Run Summary: Card analysis parameters configured.")
        print(f"  Input File: {infile} (Exists: {file_exists})")
        print(f"  Output Destination: {dest_str}")
        print(f"  Export Format: {fmt_str}")
        print(f"  Baseline Reference: {os.path.join(datadir, 'output.txt')}")
        print(f"  Verbose Logging: {'Enabled' if verbose else 'Disabled'}")
        print("Dry run complete. No calculations were run or files written.")
        return

    baseline_file = str(os.path.join(datadir, 'output.txt'))
    try:
        baseline_cards = jdecode.mtg_open_file(baseline_file, verbose=verbose)
    except Exception:
        baseline_cards = []

    lm = ngrams.build_ngram_model(baseline_cards, 3, separate_lines=True, verbose=verbose)

    try:
        stats = get_statistics(infile, lm=lm, sep=True, verbose=verbose)
    except FileNotFoundError:
        print(f"Error: Input file not found: {infile}", file=sys.stderr)
        sys.exit(1)

    out_file = sys.stdout
    if outfile:
        out_file = open(outfile, 'w', encoding='utf-8')

    try:
        if json_fmt:
            dict_stats = stats_to_dict(stats)
            out_file.write(json.dumps(dict_stats, indent=2) + '\n')
        elif csv_fmt:
            export_csv_stats(stats, out_file)
        else:
            print_statistics(stats, file=out_file)
    finally:
        if outfile and out_file != sys.stdout:
            out_file.close()

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        prog="analysis.py",
        description="Analyze card validation properties, dataset distances, and n-gram perplexity for card data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  # Analyze card validation properties and n-gram perplexity for a card dataset
  python3 scripts/analysis.py data/output.txt

  # Save statistical analysis report in structured JSON or CSV format
  python3 scripts/analysis.py data/output.txt -o summary.json
  python3 scripts/analysis.py data/output.txt --csv -o summary.csv

  # Preview analysis parameters without building language models or running calculations
  python3 scripts/analysis.py data/output.txt --dry-run
"""
    )

    io_group = parser.add_argument_group('Input / Output Options')
    io_group.add_argument('infile', nargs='?', default=None,
                        help='Encoded card file or JSON card dataset to analyze (defaults to data/output.txt).')
    io_group.add_argument('-o', '--outfile', default=None,
                        help='Path to save the analysis results (auto-detects .json or .csv from file extension).')

    proc_group = parser.add_argument_group('Processing Options')
    proc_group.add_argument('-p', '--preview', '--dry-run', dest='dry_run', action='store_true',
                        help='Print a dry run summary of analysis settings without building language models or writing output files.')
    proc_group.add_argument('-v', '--verbose', action='store_true',
                        help='Enable detailed status messages during processing.')

    fmt_group = parser.add_argument_group('Output Format Options')
    fmt_group.add_argument('-j', '--json', action='store_true',
                        help='Output statistical analysis report in structured JSON format.')
    fmt_group.add_argument('--csv', action='store_true',
                        help='Output statistical analysis report in CSV format.')

    args = parser.parse_args()
    main(args.infile, outfile=args.outfile, json_fmt=args.json, csv_fmt=args.csv, dry_run=args.dry_run, verbose=args.verbose)
