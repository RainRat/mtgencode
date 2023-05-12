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
    
parser = argparse.ArgumentParser()
parser.add_argument('filename1', help='JSON filename 1 (input)')
parser.add_argument('filename2', help='JSON filename 2 (input)')
parser.add_argument('filename3', help='JSON filename 3 (output)')
args = parser.parse_args()

jsonfile1 = args.filename1
jsonfile2 = args.filename2
jsonfile3 = args.filename3
print (jsonfile1,jsonfile2,jsonfile3)
with open(jsonfile1, encoding='utf8') as fo:
    data1 = json.load(fo)

with open(jsonfile2, encoding='latin1') as fo:
    data2 = json.load(fo)

merged_data = merge_dicts(data1, data2)

with open(jsonfile3, "w", encoding='utf8') as fo:
    json.dump(merged_data, fo)
