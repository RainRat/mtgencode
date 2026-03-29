#!/usr/bin/env python3
"""
This utility extracts a single card object from a large MTGJSON file (like
AllPrintings.json) and saves it to a smaller JSON file. This is useful for
creating targeted test data or debugging specific card processing issues
without having to load the entire dataset.
"""
import json
import argparse

def extract_card(input_file, target_set_code, target_card_name, output_file):
    print(f"Loading {input_file}... (This may take a moment)")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            # MTGJSON v4/v5 structure: { "data": { "SET_CODE": { "cards": [ ... ] } } }
            content = json.load(f)
            
        print("File loaded. Searching for card...")

        # Locate the Set
        if 'data' not in content:
            print(f"Error: 'data' key not found in {input_file}. Is this a valid MTGJSON file?")
            return

        if target_set_code not in content['data']:
            print(f"Error: Set code '{target_set_code}' not found in file.")
            return

        set_data = content['data'][target_set_code]
        cards = set_data.get('cards', [])

        # Locate the Card
        found_card = None
        for card in cards:
            # Use case-insensitive partial match to find the card
            if target_card_name.lower() in card.get('name', '').lower():
                found_card = card
                break

        # Save the Card
        if found_card:
            print(f"Found '{found_card.get('name', 'Unknown')}'! Saving to {output_file}...")
            with open(output_file, 'w', encoding='utf-8') as out_f:
                json.dump(found_card, out_f, indent=4)
            print("Done.")
        else:
            print(f"Error: Card '{target_card_name}' not found in set '{target_set_code}'.")

    except FileNotFoundError:
        print(f"Error: Could not find {input_file}.")
    except MemoryError:
        print("Error: The file is too large for your RAM.")
    except json.JSONDecodeError:
        print(f"Error: {input_file} is not a valid JSON file.")

def main():
    parser = argparse.ArgumentParser(
        description="Extract a single card from an MTGJSON file.",
        epilog='''
Example Usage:
  python3 scripts/extract_one.py data/AllPrintings.json MOM "Etali, Primal Conqueror"
  python3 scripts/extract_one.py data/Standard.json LEA "Black Lotus" -o lotus.json

Notes:
  - The card name search is case-insensitive and supports partial matches.
  - Set codes should be 3-character uppercase codes (e.g., MOM, LEA, MRD).
  - This tool is primarily used for creating small JSON files for testing.
''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("input_file", help="Path to the input JSON file (e.g., data/AllPrintings.json).")
    parser.add_argument("set_code", help="The 3-character set code (e.g., MOM, LEA).")
    parser.add_argument("card_name", help="The name of the card to extract (supports partial matches).")
    parser.add_argument("--output", "-o", default="extracted_card.json",
                        help="Path where the extracted card data will be saved. Default: extracted_card.json")

    args = parser.parse_args()

    extract_card(args.input_file, args.set_code, args.card_name, args.output)

if __name__ == "__main__":
    main()
