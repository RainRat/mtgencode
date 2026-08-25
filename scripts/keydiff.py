#!/usr/bin/env python3

def parse_keyfile(f, d, constructor = lambda x: x):
    for line in f:
        kv = [s.strip() for s in line.split(':')]
        if not len(kv) == 2:
            continue
        d[kv[0]] = constructor(kv[1])

def merge_dicts(d1, d2):
    d = {k: (d1.get(k), d2.get(k)) for k in set(d1) | set(d2)}
    return d

import sys
from contextlib import nullcontext

def open_keyfile(fname):
    if fname == '-' or fname is None:
        return nullcontext(sys.stdin)
    return open(fname, 'rt')

def main(fname1, fname2=None, verbose=True):
    if fname2 is None:
        fname2 = '-'
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

    print('shared: ' + str(len(ratios)))
    for k in sorted(ratios, key=lambda x: d2[x], reverse=True):
        print('  ' + k + ': ' + str(d2[k]) + '/' +
              str(d1[k]) + ' (' + str(ratios[k]) + ')')
    print('')

    print('1 only: ' + str(len(only_1)))
    for k in sorted(only_1, key=lambda x: d1[x], reverse=True):
        print('  ' + k + ': ' + str(d1[k]))
    print('')

    print('2 only: ' + str(len(only_2)))
    for k in sorted(only_2, key=lambda x: d2[x], reverse=True):
        print('  ' + k + ': ' + str(d2[k]))
    print('')

if __name__ == '__main__':
    
    import argparse
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

  # Compare files with verbose logging enabled
  python3 scripts/keydiff.py base_keys.txt target_keys.txt -v
'''
    )
    
    parser.add_argument('file1',
                        help='base key file to diff against')
    parser.add_argument('file2', nargs='?', default=None,
                        help='other file to compare against the baseline. Defaults to stdin (-) if omitted in non-interactive sessions.')
    parser.add_argument('-v', '--verbose', action='store_true', 
                        help='verbose output')

    args = parser.parse_args()

    if args.file2 is None:
        if sys.stdin.isatty():
            parser.print_help(sys.stderr)
            sys.exit(1)
        else:
            args.file2 = '-'

    try:
        main(args.file1, args.file2, verbose=args.verbose)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    sys.exit(0)
