#!/usr/bin/env python3
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

def process_face(name, cost, type_line, subtypes, text, stats, rarity, rarity_mapping):
    temprarity = rarity_mapping.get(rarity, rarity)
    face = {
        "name": name,
        "manaCost": cost,
        "rarity": temprarity,
        "text": text.replace("\\n", "\n"),
    }

    # supertypes, types, subtypes
    supertypes, types = utils.split_types(type_line)
    if supertypes:
        face["supertypes"] = supertypes
    face["types"] = types
    if subtypes != "":
        face["subtypes"] = subtypes.split(" ")

    if stats != "":
        pt = stats.split("/")
        if len(pt) >= 2:
            face["power"] = pt[0]
            face["toughness"] = pt[1]
        else:
            if "Planeswalker" in types:
                face["loyalty"] = stats
            elif "Battle" in types:
                face["defense"] = stats
            else:
                face["pt"] = stats

    # create "type" (full type line)
    fulltypes = type_line
    if subtypes != "":
        fulltypes = fulltypes + " — " + subtypes
    face["type"] = fulltypes

    return face

def main():
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
  5. Text: Rules text. Use "\\n" or literal newlines for new lines.
  6. Stats: Power/Toughness (3/3), Loyalty (5), or Defense (3).
  7. Rarity: Short marker (C, U, R, M, L, I) or full name (common, rare, etc.).

Multi-Faced Cards:
  To represent cards with multiple faces (e.g., Splits or Transforms), use the
  " // " separator in the relevant columns.
  Example: Name: "Front // Back", Cost: "{1}{W} // {U}", Type: "Creature // Instant"

Note: The first row is ignored if the first column is exactly "name".
''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('csv_file', help='Path to the input CSV file.')
    parser.add_argument('json_output', help='Path to the output JSON file.')
    args = parser.parse_args()

    rarity_mapping = {"R": "rare", "U": "uncommon", "C": "common", "M": "mythic", "L": "basic land", "I": "special"}

    with open(args.csv_file, encoding='utf-8') as csvfile, open(args.json_output, 'w', encoding='utf-8') as jsonfile:
        reader = csv.reader(csvfile)
        json_data = {"data": {"CUS": {"type": "custom", "cards": [], "name": "custom", "code": "CUS"}}}

        for row in reader:
            if not row or row[0] == "name":
                continue

            # Check for multi-faced cards via ' // ' in any of the 7 columns
            is_multi = any(' // ' in str(row[i]) for i in range(min(len(row), 7)))

            if is_multi:
                # Split fields
                front_args = []
                back_args = []
                for i in range(7):
                    val = row[i] if i < len(row) else ""
                    if ' // ' in val:
                        parts = val.split(' // ', 1)
                        front_args.append(parts[0])
                        back_args.append(parts[1])
                    else:
                        front_args.append(val)
                        back_args.append(val)

                card = process_face(front_args[0], front_args[1], front_args[2], front_args[3], front_args[4], front_args[5], front_args[6], rarity_mapping)
                bside = process_face(back_args[0], back_args[1], back_args[2], back_args[3], back_args[4], back_args[5], back_args[6], rarity_mapping)
                card["bside"] = bside
                card["layout"] = "transform" # Standard multi-face layout
            else:
                # Pad row if it has fewer than 7 columns
                padded_row = row + [""] * (7 - len(row))
                card = process_face(padded_row[0], padded_row[1], padded_row[2], padded_row[3], padded_row[4], padded_row[5], padded_row[6], rarity_mapping)
                card["layout"] = "normal"

            card["setCode"] = "CUS"
            json_data["data"]["CUS"]["cards"].append(card)

        json.dump(json_data, jsonfile, indent=2)

if __name__ == '__main__':
    main()
