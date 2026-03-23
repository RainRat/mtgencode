import csv
import argparse
import json
import os
import sys

# Ensure lib is in path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)
import utils

"""
This script converts a specially formatted CSV file into the JSON format
used by the MTG Card Encoder. This is useful for adding your own custom
cards to the AI training dataset.
"""

parser = argparse.ArgumentParser(
    description='Convert a CSV file of custom Magic cards into MTGJSON format.',
    epilog='''
Custom Card Workflow:
  1. Create a CSV file (e.g., custom.csv) following the format below.
  2. Convert to JSON:
     python3 scripts/csv2json.py custom.csv custom.json
  3. Merge with official data:
     python3 scripts/combinejson.py data/AllPrintings.json custom.json AllCustom.json

CSV Format (7 columns in this order):
  1. Name: The name of the card (e.g., "Giant Growth").
  2. Mana Cost: The mana symbols in braces (e.g., "{G}" or "{1}{W}{B}").
  3. Types: Supertypes and card types (e.g., "Legendary Creature").
  4. Subtypes: Subtypes separated by spaces (e.g., "Elf Warrior").
  5. Text: Rules text. Use "\\\\" for new lines.
  6. Stats: Power/Toughness (3/3), Loyalty (5), or Defense (3).
  7. Rarity: Short marker (C, U, R, M) or full name (common, rare, etc.).

Note: The first row is ignored if the first column is exactly "name".
''',
    formatter_class=argparse.RawDescriptionHelpFormatter
)
parser.add_argument('csv_file', help='Path to the input CSV file.')
parser.add_argument('json_output', help='Path to the output JSON file.')
args = parser.parse_args()

rarity_mapping = {"R": "rare", "U": "uncommon", "C": "common", "M": "mythic"}

with open(args.csv_file) as csvfile, open(args.json_output, 'w') as jsonfile:
    reader = csv.reader(csvfile)
    json_data = {"data": {"CUS": {"type": "custom", "cards": [], "name": "custom", "code": "CUS"}}}

    for row in reader:
        if row[0] == "name":
            continue
        
        temprarity = rarity_mapping.get(row[6], row[6])

        card = {
            "layout": "normal",
            "manaCost": row[1],
            "name": row[0],
            "rarity": temprarity,
            "setCode": "CUS",
            "text": row[4],
        }
        # supertypes, types, subtypes
        supertypes, types = utils.split_types(row[2])
        if supertypes:
            card["supertypes"] = supertypes
        card["types"] = types
        if row[3] != "":
            card["subtypes"] = row[3].split(" ")

        if row[5] != "":
            pt = row[5].split("/")
            if len(pt) >= 2:
                card["power"] = pt[0]
                card["toughness"] = pt[1]
            else:
                if "Planeswalker" in types:
                    card["loyalty"] = row[5]
                elif "Battle" in types:
                    card["defense"] = row[5]
                else:
                    card["pt"] = row[5]

        # create "type"
        fulltypes = row[2]
        if row[3] != "":
            fulltypes = fulltypes + " — " + row[3]
        card["type"] = fulltypes

        json_data["data"]["CUS"]["cards"].append(card)

    json.dump(json_data, jsonfile)
