import json
import argparse

def merge_dicts(dict1, dict2):
    """Recursively merge two dictionaries."""
    merged_dict = dict1.copy()
    for key, value in dict2.items():
        if key in merged_dict and isinstance(merged_dict[key], dict) and isinstance(value, dict):
            merged_dict[key] = merge_dicts(merged_dict[key], value)
        else:
            merged_dict[key] = value
    return merged_dict
    
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('filename1', help='JSON filename 1 (input)')
    parser.add_argument('filename2', help='JSON filename 2 (input)')
    parser.add_argument('filename3', help='JSON filename 3 (output)')
    args = parser.parse_args()

    try:
        with open(args.filename1, encoding='utf8') as fo:
            data1 = json.load(fo)

        with open(args.filename2, encoding='latin1') as fo:
            data2 = json.load(fo)

        merged_data = merge_dicts(data1, data2)

        with open(args.filename3, "w", encoding='utf8') as fo:
            json.dump(merged_data, fo)

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except json.JSONDecodeError as e:
        print(f"Invalid JSON file: {e}")

if __name__ == "__main__":
    main()
