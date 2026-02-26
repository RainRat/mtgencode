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
        description="Merges two card data files in JSON format. If both files contain the same set or card keys, the information from the second file is used."
    )
    parser.add_argument('base_file', help='The primary JSON file (e.g., AllPrintings.json).')
    parser.add_argument('custom_file', help='The second JSON file containing your custom cards.')
    parser.add_argument('output_file', help='The name for the new, merged JSON file.')
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
