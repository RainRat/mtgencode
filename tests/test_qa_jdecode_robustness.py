import pytest
import os
import json
import csv
from lib import jdecode

def test_mtg_open_file_uppercase_json(tmp_path):
    # Create a JSON file with uppercase extension
    d = tmp_path / "data"
    d.mkdir()
    p = d / "CARDS.JSON"
    card_data = {
        "data": {
            "SET": {
                "name": "Test Set",
                "code": "SET",
                "type": "expansion",
                "cards": [
                    {
                        "name": "Test Card",
                        "manaCost": "{W}",
                        "types": ["Creature"],
                        "rarity": "common",
                        "power": "1",
                        "toughness": "1"
                    }
                ]
            }
        }
    }
    p.write_text(json.dumps(card_data))

    # Load it using mtg_open_file
    cards = jdecode.mtg_open_file(str(p))
    assert len(cards) == 1
    assert cards[0].name == "test card"

def test_mtg_open_file_mixed_case_csv(tmp_path):
    # Create a CSV file with mixed case extension
    d = tmp_path / "data"
    d.mkdir()
    p = d / "cards.CsV"
    with open(p, 'w', encoding='utf8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'mana_cost', 'type', 'rarity', 'pt'])
        writer.writeheader()
        writer.writerow({'name': 'CSV Card', 'mana_cost': '{U}', 'type': 'Instant', 'rarity': 'rare', 'pt': ''})

    # Load it using mtg_open_file
    cards = jdecode.mtg_open_file(str(p))
    assert len(cards) == 1
    assert cards[0].name == "csv card"

def test_mtg_open_file_uppercase_decklist(tmp_path):
    # Create a decklist file with uppercase extension
    d = tmp_path / "data"
    d.mkdir()
    p = d / "MYDECK.DEK"
    p.write_text("1 Grizzly Bears\n")

    # Mocking the auto-hydration to avoid dependency on AllPrintings.json
    import unittest.mock as mock
    with mock.patch('lib.jdecode._hydrate_decklist') as mocked_hydrate:
        mocked_hydrate.return_value = [mock.MagicMock(name='Grizzly Bears')]
        cards = jdecode.mtg_open_file(str(p))
        assert mocked_hydrate.called
        # Check that it was called with the correct decklist names
        args, kwargs = mocked_hydrate.call_args
        assert 'grizzly bears' in args[0]

def test_mtg_open_file_directory_with_uppercase_files(tmp_path):
    # Create a directory with various uppercase extension files
    d = tmp_path / "set_dir"
    d.mkdir()
    (d / "CARD1.JSON").write_text(json.dumps({
        "data": {"S1": {"name": "S1", "code": "S1", "type": "expansion",
                        "cards": [{"name": "C1", "manaCost": "{R}", "types": ["Sorcery"]}]}}
    }))
    (d / "CARD2.CSV").write_text("name,mana_cost,type,rarity,pt\nC2,{G},Creature,common,2/2\n")

    # Load the directory
    cards = jdecode.mtg_open_file(str(d))
    assert len(cards) == 2
    names = [c.name for c in cards]
    assert "c1" in names
    assert "c2" in names
