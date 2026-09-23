import sys
import os
import json
import subprocess
import pytest

libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)
import cardlib
from scripts import mtg_forge

def test_apply_preset_pauperize():
    card_dict = {'name': 'Super Bear', 'type': 'Creature - Bear', 'rarity': 'rare'}
    res = mtg_forge.apply_preset(card_dict, 'pauperize')
    assert res['rarity'] == 'common'

def test_apply_preset_commanderify():
    card_dict = {'name': 'Super Bear', 'type': 'Creature - Bear'}
    res = mtg_forge.apply_preset(card_dict, 'commanderify')
    assert 'Legendary' in res['type']
    assert 'Legendary' in res['supertypes']

def test_apply_preset_invert_pt():
    card_dict = {'name': 'Asymmetric Bear', 'power': '1', 'toughness': '4', 'pt': '1/4'}
    res = mtg_forge.apply_preset(card_dict, 'invert-pt')
    assert res['power'] == '4'
    assert res['toughness'] == '1'
    assert res['pt'] == '4/1'

def test_apply_preset_french_vanilla():
    card_dict = {'name': 'Flyer', 'text': 'Flying\nDraw a card when this enters the battlefield.'}
    res = mtg_forge.apply_preset(card_dict, 'french-vanilla')
    assert res['text'] == 'Flying'

def test_apply_preset_token_creator():
    card_dict = {'name': 'Golem Spawner', 'power': '3', 'toughness': '3', 'text': 'Trample'}
    res = mtg_forge.apply_preset(card_dict, 'token-creator')
    assert 'Trample' in res['text']
    assert 'Create a 3/3 colorless Construct artifact creature token.' in res['text']

def test_apply_add_type():
    card_dict = {'name': 'Drake', 'type': 'Creature - Drake'}
    res = mtg_forge.apply_add_type(card_dict, 'Dragon')
    assert 'Drake' in res['type']
    assert 'Dragon' in res['type']

def test_apply_add_keyword():
    card_dict = {'name': 'Knight', 'text': 'First strike'}
    res = mtg_forge.apply_add_keyword(card_dict, 'Flying, Lifelink')
    assert res['text'] == 'Flying, Lifelink\nFirst strike'

def test_apply_modifiers_combined():
    class DummyArgs:
        preset = 'commanderify'
        name = None
        cost = '{2}{G}'
        type = None
        add_type = ['Elk']
        text = None
        add_keyword = ['Trample']
        pt = '3/3'
        loy = None
        rarity = None
        set = None
        color_shift = None
        buff = None
        nerf = None
        scale_up = None
        scale_down = None
        replace = None

    card_dict = {'name': 'Big Elk', 'type': 'Creature - Beast'}
    res = mtg_forge.apply_modifiers(card_dict, DummyArgs())
    assert 'Legendary' in res['type']
    assert 'Elk' in res['type']
    assert res['text'] == 'Trample'
    assert res['manaCost'] == '{2}{G}'

def test_cli_presets_single_card():
    cmd = [
        sys.executable, 'scripts/mtg_forge.py',
        '--name', 'Custom Bear',
        '--cost', '{1}{G}',
        '--type', 'Creature - Bear',
        '--pt', '2/2',
        '--preset', 'commanderify',
        '--add-keyword', 'Flying',
        '--json'
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(res.stdout)
    assert 'Legendary' in data['supertypes']
    assert 'Flying' in data['text']

def test_cli_presets_dry_run():
    cmd = [
        sys.executable, 'scripts/mtg_forge.py',
        '--name', 'Custom Bear',
        '--cost', '{1}{G}',
        '--type', 'Creature - Bear',
        '--pt', '2/2',
        '--preset', 'pauperize',
        '--dry-run'
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert 'Dry Run Summary' in res.stdout
    assert 'Common' in res.stdout
