import json
import argparse

def extract_card(input_file, target_set_code, target_card_name, output_file):
    print(f"Loading {input_file}... (This may take a moment)")
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            # MTGJSON v5 structure: { "data": { "SET_CODE": { "cards": [ ... ] } } }
            content = json.load(f)
            
        print("File loaded. Searching for card...")

        # 1. Locate the Set
        # Ensure 'data' key exists
        if 'data' not in content:
            print(f"Error: 'data' key not found in {input_file}. Is this a valid MTGJSON file?")
            return

        if target_set_code not in content['data']:
            print(f"Error: Set code '{target_set_code}' not found in file.")
            return

        set_data = content['data'][target_set_code]
        cards = set_data.get('cards', [])

        # 2. Locate the Card
        found_card = None
        for card in cards:
            # Use exact match or 'in' depending on preference. The original used 'in'.
            # I'll stick to 'in' but maybe lowercase comparison would be better?
            # The original code was: if TARGET_CARD_NAME in (card.get('name')):
            # Let's keep the original logic for now.
            if target_card_name in card.get('name', ''):
                found_card = card
                break
                # Note: If you want a specific variant (foil/alt art), 
                # you might need to check card['uuid'] or card['number'] here.

        # 3. Save the Card
        if found_card:
            print(f"Found '{found_card.get('name', 'Unknown')}'! Saving to {output_file}...")
            with open(output_file, 'w', encoding='utf-8') as out_f:
                json.dump(found_card, out_f, indent=4)
            print("Done.")
        else:
            print(f"Error: Card '{target_card_name}' not found in set '{target_set_code}'.")

    except FileNotFoundError:
        print(f"Error: Could not find {input_file} in this directory.")
    except MemoryError:
        print("Error: The file is too large for your RAM. See the 'Low Memory' tip below.")
    except json.JSONDecodeError:
        print(f"Error: {input_file} is not a valid JSON file.")

def main():
    parser = argparse.ArgumentParser(description="Extract a single card from an MTGJSON file.")
    parser.add_argument("input_file", help="Path to the input JSON file (e.g., Vintage.json)")
    parser.add_argument("set_code", help="The 3-character code for the set (e.g., MOM)")
    parser.add_argument("card_name", help="The name of the card to extract")
    parser.add_argument("--output", "-o", default="extracted_card.json", help="Path to the output JSON file")

    args = parser.parse_args()

    extract_card(args.input_file, args.set_code, args.card_name, args.output)

if __name__ == "__main__":
    main()
