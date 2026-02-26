#!/usr/bin/env python3
import sys
import os
import argparse

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

def calculate_stats(data):
    nonempty = len(data)
    name_avg = sum(float(item[2]) for item in data) / nonempty
    name_dupes = sum(float(item[2]) == 1.0 for item in data)
    card_avg = sum(float(item[3]) for item in data) / nonempty
    card_dupes = sum(float(item[3]) == 1.0 for item in data)
    return nonempty, name_avg, name_dupes, card_avg, card_dupes

def main(fname):
    with open(fname, 'rt') as f:
        cardstats = [line.split('|') for line in f if len(line.split('|')) >= 4]

    nonempty, name_avg, name_dupes, card_avg, card_dupes = calculate_stats(cardstats)

    print(str(nonempty) + ' cards')
    print('-- names --')
    print('avg distance:   ' + str(name_avg))
    print('num duplicates: ' + str(name_dupes))
    print('-- cards --')
    print('avg distance:   ' + str(card_avg))
    print('num duplicates: ' + str(card_dupes))
    print('----')

if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument('infile', #nargs='?'. default=None,
                        help='data file to process')

    args = parser.parse_args()
    main(args.infile)
