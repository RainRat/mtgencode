import sys
import os
import io
import json
from unittest.mock import patch
from lib import jdecode, utils, cardlib

def test_activate_printing_empty_set_code():
    card = cardlib.Card({"name": "Test Card", "types": ["Land"]})
    assert card.activate_printing(None) is False
    assert card.activate_printing("") is False

def test_activate_printing_rarity_fallback_and_nonexistent_set():
    card = cardlib.Card({
        "name": "Test Card",
        "types": ["Land"],
        "setCode": "SET1",
        "rarity": "Common",
        "number": "1"
    })
    card.add_printing("SET2", "CustomRarity", "2")

    assert card.activate_printing("SET2") is True
    assert card.set_code == "SET2"
    assert card.rarity == "CustomRarity"
    assert card.number == "2"

    assert card.activate_printing("SET3") is False

def test_jdecode_reprint_filtering():
    cards_json = {
        "data": {
            "SET1": {
                "code": "SET1", "name": "Set One", "type": "expansion",
                "cards": [
                    {"name": "Reborn", "manaCost": "{G}", "types": ["Instant"], "rarity": "Common", "number": "1"}
                ]
            },
            "SET2": {
                "code": "SET2", "name": "Set Two", "type": "expansion",
                "cards": [
                    {"name": "Reborn", "manaCost": "{G}", "types": ["Instant"], "rarity": "Rare", "number": "12"}
                ]
            }
        }
    }
    json_str = json.dumps(cards_json)

    with patch('sys.stdin', io.StringIO(json_str)):
        res = jdecode.mtg_open_file('-', sets=["SET2"])

    assert len(res) == 1
    matched_card = res[0]
    assert matched_card.name == "reborn"
    assert matched_card.set_code == "SET2"
    assert matched_card.rarity == "A"
    assert matched_card.number == "12"
