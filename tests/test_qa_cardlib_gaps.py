
import pytest
import sys
import os

# Ensure lib is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib')))

from cardlib import Card, fields_from_json
import utils

def test_fields_from_json_internal_rarity_markers():
    # 'O' is the marker for Common
    src_json = {
        "name": "Test Card",
        "types": ["Instant"],
        "rarity": "O"
    }
    parsed, valid, fields = fields_from_json(src_json)
    assert parsed
    assert fields['rarity'] == [(-1, 'O')]

def test_color_identity_with_text_symbols():
    src_json = {
        "name": "Green Producer",
        "manaCost": "{1}",
        "types": ["Artifact"],
        "text": "{T}: Add {G}.",
        "rarity": "Common"
    }
    card = Card(src_json)
    assert 'G' in card.color_identity
    assert len(card.color_identity) == 1

def test_display_data_ansi_mechanics_colorization():
    src_json = {
        "name": "Fast Flyer",
        "manaCost": "{1}{U}",
        "types": ["Creature"],
        "text": "Flying, Haste",
        "rarity": "Common",
        "power": "1",
        "toughness": "1"
    }
    card = Card(src_json)
    assert 'Flying' in card.mechanics
    assert 'Haste' in card.mechanics

    data = card._get_single_face_display_data(ansi_color=True)
    mechanics_idx = 7
    mechanics_str = data[mechanics_idx]

    assert utils.Ansi.CYAN in mechanics_str
    assert "Flying" in mechanics_str
    assert "Haste" in mechanics_str
    assert utils.Ansi.RESET in mechanics_str
