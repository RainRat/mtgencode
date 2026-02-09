import json
import os
import subprocess
import tempfile
import pytest

def test_csv2json_escaping():
    csv_content = 'name,manaCost,types,subtypes,text,pt,rarity\n"""Giant"" Growth","{1}","Creature","Soldier","He said ""Hello"".\\nNew line.","2/2","C"\n'
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, 'test.csv')
        json_path = os.path.join(tmpdir, 'test.json')

        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)

        # Run scripts/csv2json.py
        # We assume we are running from the root of the repo
        script_path = os.path.join(os.getcwd(), 'scripts', 'csv2json.py')
        subprocess.run(['python3', script_path, csv_path, json_path], check=True)

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        card = data['data']['CUS']['cards'][0]
        assert card['name'] == '"Giant" Growth'
        # We expect the text to be exactly as in CSV (after csv.reader parsing)
        # "He said ""Hello"".\\nNew line." in CSV -> He said "Hello".\nNew line. (literal \ and n)
        assert card['text'] == 'He said "Hello".\\nNew line.'

def test_csv2json_newlines():
    # Test with actual newlines in CSV cells (requires quoting)
    csv_content = 'name,manaCost,types,subtypes,text,pt,rarity\n"Newlines","{0}","Artifact","","Line 1\nLine 2","","C"\n'
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, 'test.csv')
        json_path = os.path.join(tmpdir, 'test.json')

        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)

        script_path = os.path.join(os.getcwd(), 'scripts', 'csv2json.py')
        subprocess.run(['python3', script_path, csv_path, json_path], check=True)

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        card = data['data']['CUS']['cards'][0]
        assert card['text'] == 'Line 1\nLine 2'
