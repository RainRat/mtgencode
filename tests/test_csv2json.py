import json
import os
import tempfile
import runpy
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

        os.remove(json_path)

        # 2. Test autodetection mode
        with patch('sys.argv', ['mtg_csv_json.py', csv_path, json_path]):
            main_direct()

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert data['data']['CUS']['cards'][0]['name'] == 'Test'

def test_csv2json_and_json2csv_script_mains():
    import scripts.csv2json as csv2json_mod
    import scripts.json2csv as json2csv_mod

    csv_content = 'name,manaCost,types,subtypes,text,pt,rarity\n"Test","{0}","Artifact","","Rules","","C"\n'
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, 'test.csv')
        json_path = os.path.join(tmpdir, 'test.json')
        csv_out_path = os.path.join(tmpdir, 'output.csv')

        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)

        with patch('sys.argv', ['csv2json.py', csv_path, json_path]):
            csv2json_mod.main()

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert data['data']['CUS']['cards'][0]['name'] == 'Test'

        with patch('sys.argv', ['json2csv.py', json_path, csv_out_path]):
            json2csv_mod.main()

        assert os.path.exists(csv_out_path)

def test_csv2json_and_json2csv_cli_entrypoints():
    csv_content = 'name,manaCost,types,subtypes,text,pt,rarity\n"Test","{0}","Artifact","","Rules","","C"\n'
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, 'test.csv')
        json_path = os.path.join(tmpdir, 'test.json')
        csv_out_path = os.path.join(tmpdir, 'output.csv')

        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)

        with patch('sys.argv', ['csv2json.py', csv_path, json_path]):
            runpy.run_path('scripts/csv2json.py', run_name='__main__')

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert data['data']['CUS']['cards'][0]['name'] == 'Test'

        with patch('sys.argv', ['json2csv.py', json_path, csv_out_path]):
            runpy.run_path('scripts/json2csv.py', run_name='__main__')

        assert os.path.exists(csv_out_path)

def test_csv2json_custom_set_code_and_name():
    csv_content = 'name,manaCost,types,subtypes,text,pt,rarity\n"Custom Dragon","{4}{R}{R}","Creature","Dragon","Flying","5/5","R"\n'
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, 'set.csv')
        json_path = os.path.join(tmpdir, 'set.json')

        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)

        # Test explicit set code and set name
        with patch('sys.argv', ['csv2json.py', csv_path, json_path, '-s', 'DRG', '-n', 'Dragons of Custom']):
            main()

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert 'DRG' in data['data']
        set_info = data['data']['DRG']
        assert set_info['code'] == 'DRG'
        assert set_info['name'] == 'Dragons of Custom'
        assert set_info['cards'][0]['name'] == 'Custom Dragon'
        assert set_info['cards'][0]['setCode'] == 'DRG'

def test_csv2json_stdin_stdout_piping():
    import io
    csv_content = 'name,manaCost,types,subtypes,text,pt,rarity\n"Piped Artifact","{1}","Artifact","","Draw a card.","","U"\n'
    stdin_mock = io.StringIO(csv_content)
    stdout_mock = io.StringIO()

    with patch('sys.stdin', stdin_mock), patch('sys.stdout', stdout_mock), patch('sys.argv', ['csv2json.py', '-', '-', '-s', 'PIPE']):
        main()

    res_json = json.loads(stdout_mock.getvalue())
    assert 'PIPE' in res_json['data']
    card = res_json['data']['PIPE']['cards'][0]
    assert card['name'] == 'Piped Artifact'
    assert card['setCode'] == 'PIPE'

def test_csv2json_batch_merge_no_collision():
    from scripts.combinejson import merge_dicts
    csv_content_1 = 'name,manaCost,types,subtypes,text,pt,rarity\n"Set 1 Card","{1}","Artifact","","","","C"\n'
    csv_content_2 = 'name,manaCost,types,subtypes,text,pt,rarity\n"Set 2 Card","{2}","Artifact","","","","U"\n'

    with tempfile.TemporaryDirectory() as tmpdir:
        csv1 = os.path.join(tmpdir, 'set1.csv')
        json1 = os.path.join(tmpdir, 'set1.json')
        csv2 = os.path.join(tmpdir, 'set2.csv')
        json2 = os.path.join(tmpdir, 'set2.json')

        with open(csv1, 'w', encoding='utf-8') as f:
            f.write(csv_content_1)
        with open(csv2, 'w', encoding='utf-8') as f:
            f.write(csv_content_2)

        with patch('sys.argv', ['csv2json.py', csv1, json1, '-s', 'CUS1']):
            main()
        with patch('sys.argv', ['csv2json.py', csv2, json2, '-s', 'CUS2']):
            main()

        with open(json1, 'r', encoding='utf-8') as f1, open(json2, 'r', encoding='utf-8') as f2:
            data1 = json.load(f1)
            data2 = json.load(f2)

        merged = merge_dicts(data1, data2)
        assert 'CUS1' in merged['data']
        assert 'CUS2' in merged['data']
        assert merged['data']['CUS1']['cards'][0]['name'] == 'Set 1 Card'
        assert merged['data']['CUS2']['cards'][0]['name'] == 'Set 2 Card'

def test_csv2json_dry_run_set_info():
    import io
    csv_content = 'name,manaCost,types,subtypes,text,pt,rarity\n"Preview Card","{0}","Artifact","","","","C"\n'
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, 'test.csv')
        with open(csv_path, 'w', encoding='utf-8') as f:
            f.write(csv_content)

        stdout_mock = io.StringIO()
        with patch('sys.stdout', stdout_mock), patch('sys.argv', ['csv2json.py', csv_path, '--dry-run', '-s', 'MY1', '-n', 'My First Set']):
            main()

        output = stdout_mock.getvalue()
        assert "=== CSV to JSON Conversion Summary (Dry Run) ===" in output
        assert "Target set code: MY1 (My First Set)" in output
        assert "Preview Card" in output
