#!/usr/bin/env python3
import sys
import os
import argparse
import json
import csv
import io
from contextlib import nullcontext

def parse_keyfile(f, d, constructor = lambda x: x):
    for line in f:
        kv = [s.strip() for s in line.split(':')]
        if not len(kv) == 2:
            continue
        d[kv[0]] = constructor(kv[1])

def merge_dicts(d1, d2):
    d = {k: (d1.get(k), d2.get(k)) for k in set(d1) | set(d2)}
    return d

def open_keyfile(fname):
    if fname == '-' or fname is None:
        return nullcontext(sys.stdin)
    return open(fname, 'rt')

def main(fname1, fname2=None, verbose=True, outfile=None, output_json=False, output_csv=False, dry_run=False):
    if fname2 is None:
        fname2 = '-'

    # Auto-detect format based on outfile extension if format flags are not explicitly set
    if outfile:
        if outfile.endswith('.json') and not output_csv:
            output_json = True
        elif outfile.endswith('.csv') and not output_json:
            output_csv = True

    if verbose:
        print('opening ' + fname1 + ' as base key/value store')
        print('opening ' + fname2 + ' as target key/value store')

    d1 = {}
    d2 = {}
    with open_keyfile(fname1) as f1:
        parse_keyfile(f1, d1, int)
    with open_keyfile(fname2) as f2:
        parse_keyfile(f2, d2, int)
    
    tot1 = sum(d1.values())
    tot2 = sum(d2.values())

    if verbose:
        print('  ' + fname1 + ': ' + str(len(d1)) + ', total ' + str(tot1))
        print('  ' + fname2 + ': ' + str(len(d2)) + ', total ' + str(tot2))

    d_merged = merge_dicts(d1, d2)

    ratios = {}
    only_1 = {}
    only_2 = {}
    for k in d_merged:
        (v1, v2) = d_merged[k]
        if v1 is None:
            only_2[k] = v2
        elif v2 is None:
            only_1[k] = v1
        else:
            if v1 == 0 or tot2 == 0:
                ratios[k] = 0.0
            else:
                ratios[k] = float(v2 * tot1) / float(v1 * tot2)

    if dry_run:
        print(f"Dry Run Summary: Evaluated key comparison between {fname1} and {fname2}.")
        print("Key Statistics:")
        print(f"  Base Keys ({fname1}): {len(d1)} key(s), total count: {tot1}")
        print(f"  Target Keys ({fname2}): {len(d2)} key(s), total count: {tot2}")
        print("Comparison Breakdown:")
        print(f"  Shared: {len(ratios)} key(s)")
        print(f"  File 1 Only: {len(only_1)} key(s)")
        print(f"  File 2 Only: {len(only_2)} key(s)")
        sorted_shared = sorted(ratios, key=lambda x: d2[x], reverse=True)[:5]
        sample_str = ", ".join(f"'{k}': {d2[k]}/{d1[k]} ({ratios[k]:.2f})" for k in sorted_shared)
        print(f"Sample Shared Ratios Preview (up to 5): {sample_str if sample_str else 'None'}")
        return

    # Structured JSON output
    if output_json:
        json_report = {
            "summary": {
                "file1": {"file": fname1, "keys": len(d1), "total": tot1},
                "file2": {"file": fname2, "keys": len(d2), "total": tot2},
                "shared_count": len(ratios),
                "only_file1_count": len(only_1),
                "only_file2_count": len(only_2)
            },
            "shared": [
                {"key": k, "count1": d1[k], "count2": d2[k], "ratio": ratios[k]}
                for k in sorted(ratios, key=lambda x: d2[x], reverse=True)
            ],
            "only_file1": [
                {"key": k, "count": d1[k]}
                for k in sorted(only_1, key=lambda x: d1[x], reverse=True)
            ],
            "only_file2": [
                {"key": k, "count": d2[k]}
                for k in sorted(only_2, key=lambda x: d2[x], reverse=True)
            ]
        }
        res_text = json.dumps(json_report, indent=2)
        if outfile:
            with open(outfile, 'w', encoding='utf-8') as f:
                f.write(res_text + '\n')
        else:
            print(res_text)
        return

    # Structured CSV output
    if output_csv:
        output_buffer = io.StringIO()
        writer = csv.writer(output_buffer)
        writer.writerow(['Category', 'Key', 'Count1', 'Count2', 'Ratio'])
        for k in sorted(ratios, key=lambda x: d2[x], reverse=True):
            writer.writerow(['Shared', k, d1[k], d2[k], ratios[k]])
        for k in sorted(only_1, key=lambda x: d1[x], reverse=True):
            writer.writerow(['File1_Only', k, d1[k], '', ''])
        for k in sorted(only_2, key=lambda x: d2[x], reverse=True):
            writer.writerow(['File2_Only', k, '', d2[k], ''])

        res_text = output_buffer.getvalue()
        if outfile:
            with open(outfile, 'w', encoding='utf-8', newline='') as f:
                f.write(res_text)
        else:
            sys.stdout.write(res_text)
        return

    # Plain Text Report output
    output_lines = []
    output_lines.append('shared: ' + str(len(ratios)))
    for k in sorted(ratios, key=lambda x: d2[x], reverse=True):
        output_lines.append('  ' + k + ': ' + str(d2[k]) + '/' +
                             str(d1[k]) + ' (' + str(ratios[k]) + ')')
    output_lines.append('')

    output_lines.append('1 only: ' + str(len(only_1)))
    for k in sorted(only_1, key=lambda x: d1[x], reverse=True):
        output_lines.append('  ' + k + ': ' + str(d1[k]))
    output_lines.append('')

    output_lines.append('2 only: ' + str(len(only_2)))
    for k in sorted(only_2, key=lambda x: d2[x], reverse=True):
        output_lines.append('  ' + k + ': ' + str(d2[k]))
    output_lines.append('')

    res_text = '\n'.join(output_lines)
    if outfile:
        with open(outfile, 'w', encoding='utf-8') as f:
            f.write(res_text)
    else:
        print(res_text)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog='keydiff.py',
        description='Compare two key/value store files and report shared keys, frequency ratios, and exclusive entries.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Usage Examples:
  # Compare two key/value store files
  python3 scripts/keydiff.py base_keys.txt target_keys.txt

  # Compare a baseline file against standard input
  cat target_keys.txt | python3 scripts/keydiff.py base_keys.txt

  # Save key difference report to JSON
  python3 scripts/keydiff.py base_keys.txt target_keys.txt -o diff.json

  # Save key difference report to CSV
  python3 scripts/keydiff.py base_keys.txt target_keys.txt --csv -o diff.csv

  # Preview key comparison statistics without writing output files (dry-run mode)
  python3 scripts/keydiff.py base_keys.txt target_keys.txt --dry-run
'''
    )

    # Group: Input / Output Options
    io_group = parser.add_argument_group('Input / Output Options')
    io_group.add_argument('file1',
                        help='Base key file to diff against.')
    io_group.add_argument('file2', nargs='?', default=None,
                        help='Other file to compare against the baseline. Defaults to stdin (-) if omitted in non-interactive sessions.')
    io_group.add_argument('-o', '--outfile',
                        help='Path to save output report. Auto-detects .json or .csv format from extension if specified.')

    # Group: Output Format Options
    fmt_group = parser.add_mutually_exclusive_group()
    fmt_group.add_argument('-j', '--json', action='store_true',
                        help='Output key comparison in structured JSON format.')
    fmt_group.add_argument('--csv', action='store_true',
                        help='Output key comparison in CSV format.')

    # Group: Processing Options
    proc_group = parser.add_argument_group('Processing Options')
    proc_group.add_argument('-p', '--preview', '--dry-run', dest='dry_run', action='store_true',
                        help='Print a dry run summary of key statistics and ratio preview to standard output without creating or modifying target output files.')
    proc_group.add_argument('-v', '--verbose', action='store_true',
                        help='Enable detailed status messages.')

    args = parser.parse_args()

    if args.file2 is None:
        if sys.stdin.isatty():
            parser.print_help(sys.stderr)
            sys.exit(1)
        else:
            args.file2 = '-'

    try:
        main(args.file1, args.file2, verbose=args.verbose, outfile=args.outfile,
             output_json=args.json, output_csv=args.csv, dry_run=args.dry_run)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    sys.exit(0)
