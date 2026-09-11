"""
Merge two Magic: The Gathering card data files in JSON format.

This utility is primarily used to combine custom card data with the official
MTGJSON dataset. By merging your own designs with official data, you can
create comprehensive datasets for AI training, validation, or mechanical
analysis.

Conflict Resolution:
If the same key (for example, a set code or card identifier) exists in both files,
the value from the second file (custom_file) will overwrite the value from
the first file (base_file).
"""
import json
import argparse
from collections import defaultdict


def merge_dicts(dict1, dict2):
    """
    Recursively merges two dictionaries.

    If a key exists in both dictionaries, the value from the second
    dictionary (dict2) will be used in the final result.
    """
    merged_dict = dict1.copy()
    for key, value in dict2.items():
        if key in merged_dict and isinstance(merged_dict[key], dict) and isinstance(value, dict):
            merged_dict[key] = merge_dicts(merged_dict[key], value)
        else:
            merged_dict[key] = value
    return merged_dict


def _summarize_dataset(merged_data):
    """
    Summarizes merged card dataset into card count, set code breakdown, and sample names.
    """
    total_cards = 0
    set_breakdown = defaultdict(int)
    sample_names = []

    def process_card(card, set_code="UNKNOWN"):
        nonlocal total_cards
        total_cards += 1
        set_breakdown[set_code] += 1
        name = card.get("name") if isinstance(card, dict) else str(card)
        if name and len(sample_names) < 10:
            sample_names.append(name)

    if isinstance(merged_data, dict):
        if "data" in merged_data and isinstance(merged_data["data"], dict):
            for set_code, set_info in merged_data["data"].items():
                if isinstance(set_info, dict) and "cards" in set_info and isinstance(set_info["cards"], list):
                    for card in set_info["cards"]:
                        process_card(card, set_code)
                elif isinstance(set_info, list):
                    for card in set_info:
                        process_card(card, set_code)
        else:
            has_sets = False
            for key, val in merged_data.items():
                if isinstance(val, dict) and "cards" in val and isinstance(val["cards"], list):
                    has_sets = True
                    for card in val["cards"]:
                        process_card(card, key)
            if not has_sets:
                if "cards" in merged_data and isinstance(merged_data["cards"], list):
                    for card in merged_data["cards"]:
                        process_card(card, merged_data.get("code", "UNKNOWN"))
                else:
                    total_cards = len(merged_data)
                    for key in list(merged_data.keys())[:10]:
                        sample_names.append(str(key))
    elif isinstance(merged_data, list):
        for card in merged_data:
            process_card(card, "UNKNOWN")

    return total_cards, set_breakdown, sample_names


def main():
    parser = argparse.ArgumentParser(
        prog="combinejson.py",
        description="Merge two Magic: The Gathering card data files in JSON format.",
        epilog='''
Custom Card Workflow:
  1. Create a CSV file containing your custom cards (see CUSTOM.md).
  2. Convert the CSV to JSON format:
     python3 scripts/csv2json.py custom.csv custom.json
  3. Merge your custom JSON with the official dataset:
     python3 scripts/combinejson.py data/AllPrintings.json custom.json AllCustom.json

Dry Run / Preview:
  Preview merged dataset statistics without writing output to disk:
  python3 scripts/combinejson.py data/AllPrintings.json my_custom_set.json --dry-run

Notes:
  - If keys conflict, data from the second file (custom_file) overwrites the first.
  - This script supports recursive dictionary merging for nested metadata.

Example:
  python3 scripts/combinejson.py data/AllPrintings.json my_custom_set.json AllCards.json
''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('base_file', help='Path to the primary JSON file (for example, data/AllPrintings.json).')
    parser.add_argument('custom_file', help='Path to the second JSON file containing your custom cards.')
    parser.add_argument('output_file', nargs='?', default=None,
                        help='Path where the merged JSON file will be saved (optional if --dry-run is specified).')

    proc_group = parser.add_argument_group('Processing Options')
    proc_group.add_argument('-p', '--preview', '--dry-run', dest='dry_run', action='store_true',
                            help='Print a summary of merged dataset stats (total matched card count, set code breakdown, and sample preview of up to 10 matching card names) to standard output without creating or modifying the target output file.')

    args = parser.parse_args()

    if not args.dry_run and not args.output_file:
        parser.error("the following arguments are required: output_file (unless --dry-run is specified)")

    try:
        with open(args.base_file, encoding='utf8') as fo:
            data1 = json.load(fo)

        with open(args.custom_file, encoding='utf8') as fo:
            data2 = json.load(fo)

        merged_data = merge_dicts(data1, data2)

        if args.dry_run:
            total_cards, set_breakdown, sample_names = _summarize_dataset(merged_data)
            print(f"Dry Run Summary: {total_cards} card(s) in merged dataset.")
            if set_breakdown:
                print("Set Code Breakdown:")
                for code, count in sorted(set_breakdown.items()):
                    print(f"  {code}: {count} card(s)")
            if sample_names:
                print(f"Sample Preview (up to 10): {', '.join(sample_names)}")
            return

        with open(args.output_file, "w", encoding='utf8') as fo:
            json.dump(merged_data, fo)

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except json.JSONDecodeError as e:
        print(f"Invalid JSON file: {e}")


if __name__ == "__main__":
    main()
