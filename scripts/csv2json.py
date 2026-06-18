#!/usr/bin/env python3
import sys
import os

# Ensure scripts dir is in path
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from mtg_csv_json import run_csv2json

def main():
    run_csv2json()

if __name__ == '__main__':
    main()
