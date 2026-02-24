import pytest
import os
import sys
import tempfile
import json
from unittest.mock import patch
from io import StringIO
import zipfile

# Add lib to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import jdecode
import utils
import cardlib

def test_parse_decklist_non_existent():
    # Covers: if not os.path.exists(fpath): return name_counts
    res = jdecode.parse_decklist("non_existent_file.txt")
    assert res == {}

def test_parse_decklist_no_count(tmp_path):
    # Covers: if count_str: (False case)
    deck_file = tmp_path / "deck.txt"
    deck_file.write_text("Grizzly Bears")
    res = jdecode.parse_decklist(str(deck_file))
    assert res["grizzly bears"] == 1

def test_parse_decklist_exclusions(tmp_path):
    # Covers: if name_lower in ['sideboard', 'deck', 'maybeboard']: continue
    deck_file = tmp_path / "deck.txt"
    deck_file.write_text("Maybeboard\n1 Grizzly Bears\nSideboard\n1 Black Lotus")
    res = jdecode.parse_decklist(str(deck_file))
    assert "maybeboard" not in res
    assert "sideboard" not in res
    assert res["grizzly bears"] == 1
    assert res["black lotus"] == 1

def test_mtg_open_file_verbose_decklist(tmp_path, capsys):
    # Covers: if verbose: print(f"Loaded decklist from ...")
    deck_file = tmp_path / "deck.txt"
    deck_file.write_text("1 Grizzly Bears")

    # Just to make it run through without error
    json_file = tmp_path / "data.json"
    json_file.write_text(json.dumps({"data": {"S": {"code":"S", "name":"S", "type":"expansion", "cards":[]}}}))

    jdecode.mtg_open_file(str(json_file), verbose=True, decklist_file=str(deck_file))
    captured = capsys.readouterr()
    assert "Loaded decklist from" in captured.err

def test_mtg_open_file_missing_cards_warning(tmp_path, capsys):
    # Covers: if missing: print(f"Warning: {len(missing)} cards from decklist not found ...")
    deck_file = tmp_path / "deck.txt"
    deck_file.write_text("1 Missing Card")

    json_file = tmp_path / "data.json"
    json_file.write_text(json.dumps({"data": {"S": {"code":"S", "name":"S", "type":"expansion", "cards":[]}}}))

    jdecode.mtg_open_file(str(json_file), verbose=True, decklist_file=str(deck_file))
    captured = capsys.readouterr()
    assert "cards from decklist not found in source" in captured.err

def test_rarity_filter_integration(tmp_path):
    # Covers: if not card.rarity: return False
    # Card with no rarity
    data = {"data": {"S": {"code":"S", "name":"S", "type":"expansion", "cards": [{"name": "NoRarity", "types": ["Land"]}]}}}
    json_file = tmp_path / "data.json"
    json_file.write_text(json.dumps(data))

    # Filter by rarity 'Common'
    cards = jdecode.mtg_open_file(str(json_file), rarities=['Common'])
    assert len(cards) == 0

def test_mtg_open_file_dir_invalid_json(tmp_path):
    # Covers: except json.JSONDecodeError: pass
    d = tmp_path / "dir"
    d.mkdir()
    (d / "bad.json").write_text("invalid json")

    # Should not crash
    cards = jdecode.mtg_open_file(str(d))
    assert len(cards) == 0

def test_mtg_open_file_dir_mse_missing_set(tmp_path, capsys):
    # Covers: except KeyError: if verbose: print(f"Warning: 'set' file not found in nested MSE file {f}")
    d = tmp_path / "dir"
    d.mkdir()
    mse_path = d / "bad.mse-set"
    with zipfile.ZipFile(mse_path, 'w') as zf:
        zf.writestr('not_set', 'content')

    jdecode.mtg_open_file(str(d), verbose=True)
    captured = capsys.readouterr()
    assert "'set' file not found in nested MSE file" in captured.err

def test_mtg_open_file_dir_exclude_types_skip(tmp_path):
    # Covers: if exclude_types(cardtype): skip = True (for .txt files in directory)
    d = tmp_path / "dir"
    d.mkdir()
    # A conspiracy card which is excluded by default
    # |5conspiracy|0O|1Worldknit| (labeled format)
    # default fmt_ordered: [field_types, field_pt, field_loyalty, field_text, field_cost, field_name, field_rarity]
    # |5conspiracy|0O|1Worldknit| matches labeled format markers
    (d / "cards.txt").write_text("|5conspiracy|0O|1Worldknit|")

    cards = jdecode.mtg_open_file(str(d))
    assert len(cards) == 0

def test_mtg_open_jsonl_empty():
    # Covers: line 180 return {}, set() in mtg_open_jsonl_content
    res = jdecode.mtg_open_jsonl_content("")
    assert res == ({}, set())

def test_mtg_open_csv_no_pt():
    # Covers: row.get('power')/('toughness') False cases
    csv_content = "name,type,rarity\nCard,Land,Common"
    import csv
    reader = csv.DictReader(StringIO(csv_content))
    srcs, _ = jdecode.mtg_open_csv_reader(reader)
    assert "card" in srcs
    card_dict = srcs["card"][0]
    assert 'power' not in card_dict
    assert 'toughness' not in card_dict

def test_mtg_open_csv_loyalty_defense():
    # Covers: row.get('loyalty') and row.get('defense') True cases
    csv_content = "name,type,rarity,loyalty,defense\nPW,Planeswalker,Rare,3,\nBattle,Battle,Rare,,5"
    import csv
    reader = csv.DictReader(StringIO(csv_content))
    srcs, _ = jdecode.mtg_open_csv_reader(reader)
    assert srcs["pw"][0]["loyalty"] == "3"
    assert srcs["battle"][0]["defense"] == "5"

def test_mtg_open_csv_pt():
    # Covers: row.get('power') and row.get('toughness') True cases
    csv_content = "name,type,rarity,power,toughness\nCreature,Creature,Common,2,3"
    import csv
    reader = csv.DictReader(StringIO(csv_content))
    srcs, _ = jdecode.mtg_open_csv_reader(reader)
    assert srcs["creature"][0]["power"] == "2"
    assert srcs["creature"][0]["toughness"] == "3"

def test_mtg_open_csv_subtypes():
    # Covers: row.get('subtypes') True case
    csv_content = "name,type,subtypes,rarity\nSub,Creature,Elf Wizard,Common"
    import csv
    reader = csv.DictReader(StringIO(csv_content))
    srcs, _ = jdecode.mtg_open_csv_reader(reader)
    assert srcs["sub"][0]["subtypes"] == ["Elf", "Wizard"]

def test_mtg_open_csv_duplicate_name():
    # Covers: srcs[cardname].append(card_dict)
    csv_content = "name,type,rarity\nCard,Land,Common\nCard,Instant,Common"
    import csv
    reader = csv.DictReader(StringIO(csv_content))
    srcs, _ = jdecode.mtg_open_csv_reader(reader)
    assert len(srcs["card"]) == 2
