import csv
import argparse
import json

#convert a CSV file (that follows a specific format) to JSON, If you want to have custom cards in whole or part of your training.

# 1. Edit custom.csv (or create your own .csv) following the format in custom.csv
# 2. Convert your custom.csv to json, i.e. "python csv2json.py custom.csv custom.json"
# 3. Merge your json with the full official json, i.e. "python combinejson.py AllPrintings.json custom.json AllCustom.json"

parser = argparse.ArgumentParser(
    description='Converts a CSV file of custom Magic cards into MTGJSON format.',
    epilog='''
CSV Format:
  The CSV must have at least 7 columns in this order:
  1. Name (e.g., "Giant Growth")
  2. Mana Cost (e.g., "{G}")
  3. Types & Supertypes (e.g., "Legendary Creature")
  4. Subtypes (e.g., "Elf Warrior")
  5. Rules Text (e.g., "Target creature gets +3/+3 until end of turn.")
  6. P/T (e.g., "3/3")
  7. Rarity (e.g., "C", "U", "R", "M")

  The first row (header) is ignored if the first column is exactly "name".
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
        if row[5] != "":
            pt = row[5].split("/")
            card["power"] = pt[0]
            card["toughness"] = pt[1]

        # supertypes, types, subtypes
        known_supertypes = {'Legendary', 'Basic', 'Snow', 'World', 'Ongoing'}
        supertypes = []
        types = []
        for t in row[2].split():
            if t in known_supertypes:
                supertypes.append(t)
            else:
                types.append(t)
        if supertypes:
            card["supertypes"] = supertypes
        card["types"] = types
        if row[3] != "":
            card["subtypes"] = row[3].split(" ")

        # create "type"
        fulltypes = row[2]
        if row[3] != "":
            fulltypes = fulltypes + " — " + row[3]
        card["type"] = fulltypes

        json_data["data"]["CUS"]["cards"].append(card)

    json.dump(json_data, jsonfile)
