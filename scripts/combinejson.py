"""
Merge two Magic: The Gathering card data files in JSON format.

This utility is primarily used to combine custom card data with the official
MTGJSON dataset. By merging your own designs with official data, you can
create comprehensive datasets for AI training, validation, or mechanical
analysis.

Conflict Resolution:
If the same key (e.g., a set code or card identifier) exists in both files,
the value from the second file (custom_file) will overwrite the value from
the first file (base_file).
"""
import json
import argparse

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
    
def main():
    parser = argparse.ArgumentParser(
        description="Merge two Magic: The Gathering card data files in JSON format.",
        epilog='''
Custom Card Workflow:
  1. Create a CSV file containing your custom cards (see CUSTOM.md).
  2. Convert the CSV to JSON format:
     python3 scripts/csv2json.py custom.csv custom.json
  3. Merge your custom JSON with the official dataset:
     python3 scripts/combinejson.py data/AllPrintings.json custom.json AllCustom.json

Notes:
  - If keys conflict, data from the second file (custom_file) overwrites the first.
  - This script supports recursive dictionary merging for nested metadata.

Example:
  python3 scripts/combinejson.py data/AllPrintings.json my_custom_set.json AllCards.json
''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('base_file', help='Path to the primary JSON file (e.g., data/AllPrintings.json).')
    parser.add_argument('custom_file', help='Path to the second JSON file containing your custom cards.')
    parser.add_argument('output_file', help='Path where the merged JSON file will be saved.')
    args = parser.parse_args()

    try:
        with open(args.base_file, encoding='utf8') as fo:
            data1 = json.load(fo)

        with open(args.custom_file, encoding='latin1') as fo:
            data2 = json.load(fo)

        merged_data = merge_dicts(data1, data2)

        with open(args.output_file, "w", encoding='utf8') as fo:
            json.dump(merged_data, fo)

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except json.JSONDecodeError as e:
        print(f"Invalid JSON file: {e}")

if __name__ == "__main__":
    main()
