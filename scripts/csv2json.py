import csv
import argparse
import json

#convert a CSV file (that follows a specific format) to JSON, If you want to have custom cards in whole or part of your training.

# 1. Edit custom.csv (or create your own .csv) following the format in custom.csv
# 2. Convert your custom.csv to json, i.e. "python csv2json.py custom.csv custom.json"
# 3. Merge your json with the full official json, i.e. "python combinejson.py AllPrintings.json custom.json AllCustom.json"

parser = argparse.ArgumentParser()
parser.add_argument('filename1', help='CSV filename (input)')
parser.add_argument('filename2', help='JSON filename (output)')
args = parser.parse_args()

csvfile = open(args.filename1)
jsonfile = open(args.filename2, 'w')
spamreader = csv.reader(csvfile)

json_data = {"data": {"CUS": {"type": "custom", "cards": [], "name": "custom", "code": "CUS"}}}
for row in spamreader:
    if row[0] == "name":
        continue
    temprarity=row[6]
    if temprarity=="R":
        temprarity="rare"
    if temprarity=="U":
        temprarity="uncommon"
    if temprarity=="C":
        temprarity="common"
    if temprarity=="M":
        temprarity="mythic"
    card = {
        "layout": "normal",
        "manaCost": row[1],
        "name": row[0].replace("\"", ""),
        "rarity": temprarity,
        "setCode": "CUS",
        "text": row[4].replace("\\", "\\n").replace("\"", "\\\""),
    }
    if row[5] != "":
        pt = row[5].split("/")
        card["power"] = pt[0]
        card["toughness"] = pt[1]

    # supertypes, types, subtypes
    typelist = row[2].split(" ")
    if typelist[0] == "Legendary":
        card["supertypes"] = [typelist[0]]
        typelist.remove("Legendary")
    card["types"] = typelist
    if row[3] != "":
        card["subtypes"] = row[3].split(" ")

    # create "type"
    fulltypes = row[2]
    if row[3] != "":
        fulltypes = fulltypes + " — " + row[3]
    card["type"] = fulltypes

    json_data["data"]["CUS"]["cards"].append(card)

json.dump(json_data, jsonfile)
