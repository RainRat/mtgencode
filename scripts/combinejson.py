"""
This script merges two Magic: The Gathering card data files in JSON format.
It is primarily used to combine custom card data with the official MTGJSON
dataset, allowing you to include your own designs in AI training or analysis.
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
  1. Create a CSV file with your custom cards.
  2. Convert the CSV to JSON:
     python3 scripts/csv2json.py custom.csv custom.json
  3. Merge with official data:
     python3 scripts/combinejson.py data/AllPrintings.json custom.json AllCustom.json

Example:
  python3 scripts/combinejson.py data/AllPrintings.json my_set.json AllCards.json
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
