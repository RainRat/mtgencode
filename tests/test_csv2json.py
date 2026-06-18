import json
import os
import tempfile
import unittest
from unittest.mock import patch
from scripts.csv2json import main

def run_csv2json(csv_path, json_path):
    with patch('sys.argv', ['csv2json.py', csv_path, json_path]):
        main()

def test_csv2json_escaping():
    csv_content = 'name,manaCost,types,subtypes,text,pt,rarity\n"""Giant"" Growth","{1}","Creature","Soldier","He said ""Hello"".\nNew line.","2/2","C"\n'
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, 'test.csv')
        json_path = os.path.join(tmpdir, 'test.json')

        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)

        run_csv2json(csv_path, json_path)

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

        run_csv2json(csv_path, json_path)

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        card = data['data']['CUS']['cards'][0]
        assert card['text'] == 'Line 1\nLine 2'

def test_csv2json_multi_face():
    # Test multi-face detection and splitting
    csv_content = 'name,manaCost,types,subtypes,text,pt,rarity\n'
    # Test " // " in Name, Cost, Type, PT
    csv_content += 'Legendary Front // Back,{1}{W} // {U},Legendary Creature // Instant,Soldier // ,Text A // Text B,1/1 // 3,R\n'
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, 'multi.csv')
        json_path = os.path.join(tmpdir, 'multi.json')

        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)

        run_csv2json(csv_path, json_path)

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        card = data['data']['CUS']['cards'][0]
        assert card['name'] == 'Legendary Front'
        assert 'supertypes' in card
        assert card['supertypes'] == ['Legendary']
        assert card['manaCost'] == '{1}{W}'
        assert card['layout'] == 'transform'
        assert 'bside' in card
        assert card['bside']['name'] == 'Back'
        assert card['bside']['manaCost'] == '{U}'
        assert card['bside']['text'] == 'Text B'
        assert card['bside']['pt'] == '3'

def test_csv2json_special_types():
    # Test Planeswalker and Battle stat mapping
    csv_content = 'name,manaCost,types,subtypes,text,pt,rarity\n'
    csv_content += 'Jace,{1}{U}{U},Planeswalker,Jace,Rules,3,M\n'
    csv_content += 'Invasion,{1}{G},Battle,Tarkir,Rules,5,R\n'
    csv_content += 'NonCreature,{0},Artifact,,Rules,7,C\n' # Trigger "pt" mapping for non-creature/PW/Battle
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, 'special.csv')
        json_path = os.path.join(tmpdir, 'special.json')

        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)

        run_csv2json(csv_path, json_path)

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        jace = data['data']['CUS']['cards'][0]
        assert jace['name'] == 'Jace'
        assert jace['loyalty'] == '3'
        assert 'power' not in jace

        invasion = data['data']['CUS']['cards'][1]
        assert invasion['name'] == 'Invasion'
        assert invasion['defense'] == '5'
        assert 'power' not in invasion

        artifact = data['data']['CUS']['cards'][2]
        assert artifact['pt'] == '7'

def test_csv2json_padding_and_empty():
    # Test padding for rows with fewer columns and handling of empty lines
    csv_content = 'name,manaCost,types,subtypes,text,pt,rarity\n'
    csv_content += 'Short Card,{0},Artifact\n' # Only 3 columns
    csv_content += 'Multi Short // Card,{0} // {1},Artifact\n' # Only 3 columns for multi
    csv_content += '\n' # Empty line
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, 'short.csv')
        json_path = os.path.join(tmpdir, 'short.json')

        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)

        run_csv2json(csv_path, json_path)

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cards = data['data']['CUS']['cards']
        assert len(cards) == 2
        assert cards[0]['name'] == 'Short Card'
        assert cards[0]['rarity'] == '' # Default for padded rarity
        assert cards[1]['name'] == 'Multi Short'
        assert cards[1]['bside']['name'] == 'Card'

def test_mtg_csv_json_direct():
    from scripts.mtg_csv_json import main as main_direct
    csv_content = 'name,manaCost,types,subtypes,text,pt,rarity\n"Test","{0}","Artifact","","Rules","","C"\n'
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, 'test.csv')
        json_path = os.path.join(tmpdir, 'test.json')

        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)

        # 1. Test explicit subcommand mode
        with patch('sys.argv', ['mtg_csv_json.py', 'csv2json', csv_path, json_path]):
            main_direct()

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert data['data']['CUS']['cards'][0]['name'] == 'Test'

        # Clear output
        os.remove(json_path)

        # 2. Test autodetection mode
        with patch('sys.argv', ['mtg_csv_json.py', csv_path, json_path]):
            main_direct()

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert data['data']['CUS']['cards'][0]['name'] == 'Test'
