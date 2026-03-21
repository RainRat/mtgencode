import json
import os
import subprocess
import tempfile
import csv
import sys

def test_json2csv_basic_conversion():
    card_data = {
        "data": {
            "TEST": {
                "name": "Test Set",
                "code": "TEST",
                "type": "expansion",
                "cards": [
                    {
                        "name": "Grizzly Bears",
                        "manaCost": "{1}{G}",
                        "types": ["Creature"],
                        "subtypes": ["Bear"],
                        "rarity": "Common",
                        "power": "2",
                        "toughness": "2",
                        "text": "When Grizzly Bears enters the battlefield, you win."
                    }
                ]
            }
        }
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, 'input.json')
        csv_path = os.path.join(tmpdir, 'output.csv')

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(card_data, f)

        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'json2csv.py'))
        subprocess.run([sys.executable, script_path, json_path, csv_path], check=True)

        with open(csv_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        row = rows[0]
        assert row['name'] == 'grizzly bears'
        assert row['mana_cost'] == '{1}{G}'
        assert row['type'] == 'creature'
        assert row['subtypes'] == 'bear'
        assert row['text'] == 'When Grizzly Bears enters the battlefield, you win.'
        assert row['pt'] == '2/2'
        assert row['rarity'] == 'C'

def test_json2csv_stats_handling():
    card_data = {
        "data": {
            "TEST": {
                "name": "Test Set",
                "code": "TEST",
                "type": "expansion",
                "cards": [
                    {
                        "name": "Jace",
                        "types": ["Planeswalker"],
                        "rarity": "Mythic",
                        "loyalty": "3"
                    },
                    {
                        "name": "Invasion",
                        "types": ["Battle"],
                        "rarity": "Rare",
                        "defense": "5"
                    }
                ]
            }
        }
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, 'input.json')
        csv_path = os.path.join(tmpdir, 'output.csv')

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(card_data, f)

        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'json2csv.py'))
        subprocess.run([sys.executable, script_path, json_path, csv_path], check=True)

        with open(csv_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            rows = sorted(list(reader), key=lambda x: x['name'])

        assert len(rows) == 2
        assert rows[0]['name'] == 'invasion'
        assert rows[0]['pt'] == '5'
        assert rows[1]['name'] == 'jace'
        assert rows[1]['pt'] == '3'

def test_json2csv_set_filtering():
    card_data = {
        "data": {
            "SET1": {
                "name": "Set 1",
                "code": "SET1",
                "type": "expansion",
                "cards": [{"name": "Card A", "types": ["Instant"], "rarity": "Common"}]
            },
            "SET2": {
                "name": "Set 2",
                "code": "SET2",
                "type": "expansion",
                "cards": [{"name": "Card B", "types": ["Instant"], "rarity": "Common"}]
            }
        }
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, 'input.json')
        csv_path = os.path.join(tmpdir, 'output.csv')

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(card_data, f)

        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'json2csv.py'))
        subprocess.run([sys.executable, script_path, json_path, csv_path, '--set', 'SET1'], check=True)

        with open(csv_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]['name'] == 'card a'

def test_json2csv_text_unpassing():
    card_data = {
        "data": {
            "TEST": {
                "name": "Gideon",
                "code": "TEST",
                "type": "expansion",
                "cards": [
                    {
                        "name": "Gideon",
                        "types": ["Planeswalker"],
                        "rarity": "Mythic",
                        "text": "+1: Put a % counter on @.",
                        "loyalty": "4"
                    }
                ]
            }
        }
    }

    encoded_text = "|1Gideon|5Planeswalker|7mythic|8|9+1: put a % counter on @. \\ countertype % loyalty|3|0Y|"

    with tempfile.TemporaryDirectory() as tmpdir:
        txt_path = os.path.join(tmpdir, 'input.txt')
        csv_path = os.path.join(tmpdir, 'output.csv')

        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(encoded_text)

        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'json2csv.py'))
        subprocess.run([sys.executable, script_path, txt_path, csv_path], check=True)

        with open(csv_path, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]['text'].strip() == '+1: Put a loyalty counter on Gideon.'
