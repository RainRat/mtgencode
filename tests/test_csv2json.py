import json
import os
import tempfile
import csv
import sys
from unittest.mock import patch
from scripts.csv2json import main as csv2json_main

def test_csv2json_escaping():
    csv_content = 'name,manaCost,types,subtypes,text,pt,rarity\n"""Giant"" Growth","{1}","Creature","Soldier","He said ""Hello"".\\nNew line.","2/2","C"\n'
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, 'test.csv')
        json_path = os.path.join(tmpdir, 'test.json')

        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)

        with patch('sys.argv', ['csv2json.py', csv_path, json_path]):
            csv2json_main()

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        card = data['data']['CUS']['cards'][0]
        assert card['name'] == '"Giant" Growth'
        assert card['text'] == 'He said "Hello".\nNew line.'

def test_csv2json_newlines():
    csv_content = 'name,manaCost,types,subtypes,text,pt,rarity\n"Newlines","{0}","Artifact","","Line 1\nLine 2","","C"\n'
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, 'test.csv')
        json_path = os.path.join(tmpdir, 'test.json')

        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)

        with patch('sys.argv', ['csv2json.py', csv_path, json_path]):
            csv2json_main()

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        card = data['data']['CUS']['cards'][0]
        assert card['text'] == 'Line 1\nLine 2'

def test_csv2json_multifaced_text_only():
    # Test multi-faced card where only rules text differs (checks the is_multi fix)
    csv_content = 'name,manaCost,types,subtypes,text,pt,rarity\n"Split","{R}","Instant","","Front // Back","","U"\n'
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, 'test.csv')
        json_path = os.path.join(tmpdir, 'test.json')

        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)

        with patch('sys.argv', ['csv2json.py', csv_path, json_path]):
            csv2json_main()

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        card = data['data']['CUS']['cards'][0]
        assert card['layout'] == 'transform'
        assert card['text'] == 'Front'
        assert card['bside']['text'] == 'Back'
        assert card['name'] == 'Split'
        assert card['bside']['name'] == 'Split'

def test_csv2json_short_row():
    # Test that short rows are handled (padded with empty strings)
    csv_content = 'name,manaCost,types\n"Short Card","{G}","Enchantment"\n'
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, 'test.csv')
        json_path = os.path.join(tmpdir, 'test.json')

        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)

        with patch('sys.argv', ['csv2json.py', csv_path, json_path]):
            csv2json_main()

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        card = data['data']['CUS']['cards'][0]
        assert card['name'] == 'Short Card'
        assert card['types'] == ['Enchantment']
        assert card['rarity'] == ''
