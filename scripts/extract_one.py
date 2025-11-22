import json

# --- CONFIGURATION ---
INPUT_FILE = 'Vintage.json'
OUTPUT_FILE = 'extracted_card.json'

# The 3-character code for the set (e.g., 'LEA' for Alpha, 'ZEN' for Zendikar)
TARGET_SET_CODE = 'MOM' 

# The exact name of the card you want
TARGET_CARD_NAME = 'Invasion of Tarkir'

# Optional: If you know the specific UUID, you can use that instead to be exact
# TARGET_UUID = "..." 
# ---------------------

def extract_card():
    print(f"Loading {INPUT_FILE}... (This may take a moment)")
    
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            # MTGJSON v5 structure: { "data": { "SET_CODE": { "cards": [ ... ] } } }
            content = json.load(f)
            
        print("File loaded. Searching for card...")

        # 1. Locate the Set
        if TARGET_SET_CODE not in content['data']:
            print(f"Error: Set code '{TARGET_SET_CODE}' not found in file.")
            return

        set_data = content['data'][TARGET_SET_CODE]
        cards = set_data.get('cards', [])

        # 2. Locate the Card
        found_card = None
        for card in cards:
            if TARGET_CARD_NAME in (card.get('name')):
                found_card = card
                break
                # Note: If you want a specific variant (foil/alt art), 
                # you might need to check card['uuid'] or card['number'] here.

        # 3. Save the Card
        if found_card:
            print(f"Found '{TARGET_CARD_NAME}'! Saving to {OUTPUT_FILE}...")
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as out_f:
                json.dump(found_card, out_f, indent=4)
            print("Done.")
        else:
            print(f"Error: Card '{TARGET_CARD_NAME}' not found in set '{TARGET_SET_CODE}'.")

    except FileNotFoundError:
        print(f"Error: Could not find {INPUT_FILE} in this directory.")
    except MemoryError:
        print("Error: The file is too large for your RAM. See the 'Low Memory' tip below.")

if __name__ == "__main__":
    extract_card()