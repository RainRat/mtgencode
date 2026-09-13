import os
import sys
import csv
import pytest
from unittest.mock import patch

# Ensure repo root and lib/scripts are in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

import mtg_forge

def test_single_card_csv_flag(capsys):
    test_args = [
        'mtg_forge.py',
        '--name', 'CSV Elemental',
        '--cost', '{1}{U}',
        '--type', 'Creature - Elemental',
        '--pt', '2/1',
        '--text', 'Flying',
        '--rarity', 'uncommon',
        '--csv'
    ]
    with patch.object(sys, 'argv', test_args):
        mtg_forge.main()

    captured = capsys.readouterr()
    rows = list(csv.reader(captured.out.strip().splitlines()))
    assert len(rows) == 2
    assert rows[0] == ['name', 'mana_cost', 'type', 'subtypes', 'text', 'pt', 'rarity']
    assert rows[1][0] == 'csv elemental'
    assert rows[1][1] == '{1}{U}'
    assert rows[1][2] == 'creature'
    assert rows[1][3] == 'elemental'
    assert rows[1][4] == 'Flying'
    assert rows[1][5] == '2/1'
    assert rows[1][6] in ('U', 'N', 'uncommon')

def test_single_card_csv_outfile_autodetect(tmp_path):
    out_file = tmp_path / "forged_card.csv"
    test_args = [
        'mtg_forge.py',
        '--name', 'Auto CSV Spitter',
        '--cost', '{R}',
        '--type', 'Goblin',
        '--pt', '1/1',
        '--outfile', str(out_file)
    ]
    with patch.object(sys, 'argv', test_args):
        mtg_forge.main()

    assert out_file.exists()
    with open(out_file, 'r', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    assert len(rows) == 2
    assert rows[0] == ['name', 'mana_cost', 'type', 'subtypes', 'text', 'pt', 'rarity']
    assert rows[1][0] == 'auto csv spitter'

def test_batch_mode_csv(tmp_path):
    in_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../testdata/uthros.json'))
    out_file = tmp_path / "modified_batch.csv"

    test_args = [
        'mtg_forge.py',
        '--infile', in_file,
        '--batch',
        '--buff', '1',
        '--csv',
        '--outfile', str(out_file)
    ]
    with patch.object(sys, 'argv', test_args):
        mtg_forge.main()

    assert out_file.exists()
    with open(out_file, 'r', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    assert len(rows) == 2
    assert rows[0] == ['name', 'mana_cost', 'type', 'subtypes', 'text', 'pt', 'rarity']
    assert rows[1][0] == 'uthros research craft'
    # Buffed stats: power=1, toughness=9 for uthros (was 0/8) -> '1/9'
    assert rows[1][5] == '1/9'
