import os
import sys
import pytest
import tempfile
import json

# Ensure lib is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib import jdecode, cardlib

@pytest.fixture
def sample_cards_file():
    cards_data = [
        {
            "name": "Fire Dragon",
            "types": ["Creature"],
            "subtypes": ["Dragon"],
            "text": "Flying\n{R}: Fire Dragon deals 1 damage.",
            "manaCost": "{4}{R}{R}",
            "power": "5",
            "toughness": "5",
            "rarity": "rare"
        },
        {
            "name": "Water Elemental",
            "types": ["Creature"],
            "subtypes": ["Elemental"],
            "text": "Islandwalk",
            "manaCost": "{3}{U}{U}",
            "power": "5",
            "toughness": "4",
            "rarity": "uncommon"
        },
        {
            "name": "Fireball",
            "types": ["Sorcery"],
            "text": "Fireball deals X damage.",
            "manaCost": "{X}{R}",
            "rarity": "uncommon"
        },
        {
            "name": "Island",
            "types": ["Land"],
            "text": "{T}: Add {U}.",
            "rarity": "common"
        }
    ]
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False, encoding='utf-8') as tmp:
        json.dump(cards_data, tmp)
        tmp_path = tmp.name
    yield tmp_path
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

def test_generic_grep(sample_cards_file):
    # Grep for "Dragon"
    cards = jdecode.mtg_open_file(sample_cards_file, grep=["Dragon"])
    assert len(cards) == 1
    assert cards[0].name == "fire dragon"

    # Grep for "Fire" (matches name and text)
    cards = jdecode.mtg_open_file(sample_cards_file, grep=["Fire"])
    assert len(cards) == 2
    names = [c.name for c in cards]
    assert "fire dragon" in names
    assert "fireball" in names

    # Multiple greps (AND logic)
    cards = jdecode.mtg_open_file(sample_cards_file, grep=["Fire", "Dragon"])
    assert len(cards) == 1
    assert cards[0].name == "fire dragon"

def test_generic_vgrep(sample_cards_file):
    # Vgrep for "Dragon"
    cards = jdecode.mtg_open_file(sample_cards_file, vgrep=["Dragon"])
    assert len(cards) == 3
    names = [c.name for c in cards]
    assert "fire dragon" not in names
    assert "water elemental" in names

    # Multiple vgreps (OR logic)
    cards = jdecode.mtg_open_file(sample_cards_file, vgrep=["Dragon", "Elemental"])
    assert len(cards) == 2
    names = [c.name for c in cards]
    assert "fireball" in names
    assert "island" in names

def test_refined_grep(sample_cards_file):
    # Grep name
    cards = jdecode.mtg_open_file(sample_cards_file, grep_name=["Fire"])
    assert len(cards) == 2
    
    # Grep types/subtypes
    cards = jdecode.mtg_open_file(sample_cards_file, grep_types=["Creature"])
    assert len(cards) == 2
    cards = jdecode.mtg_open_file(sample_cards_file, grep_types=["Dragon"])
    assert len(cards) == 1

    # Grep text
    cards = jdecode.mtg_open_file(sample_cards_file, grep_text=["Islandwalk"])
    assert len(cards) == 1
    assert cards[0].name == "water elemental"

def test_refined_vgrep(sample_cards_file):
    # Exclude by name
    cards = jdecode.mtg_open_file(sample_cards_file, vgrep_name=["Fire"])
    assert len(cards) == 2
    names = [c.name for c in cards]
    assert "water elemental" in names
    assert "island" in names

    # Exclude by type
    cards = jdecode.mtg_open_file(sample_cards_file, vgrep_types=["Creature"])
    assert len(cards) == 2
    names = [c.name for c in cards]
    assert "fireball" in names
    assert "island" in names

    # Exclude by text
    cards = jdecode.mtg_open_file(sample_cards_file, vgrep_text=["deals"])
    assert len(cards) == 2
    assert "water elemental" in [c.name for c in cards]

def test_combined_filters(sample_cards_file):
    # Generic grep and vgrep
    cards = jdecode.mtg_open_file(sample_cards_file, grep=["Fire"], vgrep=["Sorcery"])
    assert len(cards) == 1
    assert cards[0].name == "fire dragon"

    # Refined combined
    cards = jdecode.mtg_open_file(sample_cards_file, grep_name=["Fire"], grep_types=["Sorcery"])
    assert len(cards) == 1
    assert cards[0].name == "fireball"

def test_grep_encoded_text():
    encoded_text = (
        "|1Fire Dragon|5Creature|6Dragon|3{4}{R}{R}|7rare|85/5|9Flying\\{R}: Fire Dragon deals 1 damage.\n\n"
        "|1Water Elemental|5Creature|6Elemental|3{3}{U}{U}|7uncommon|85/4|9Islandwalk\n\n"
    )

    with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False, encoding='utf-8') as tmp:
        tmp.write(encoded_text)
        tmp_path = tmp.name

    try:
        cards = jdecode.mtg_open_file(tmp_path, grep=["Elemental"])
        assert len(cards) == 1
        assert cards[0].name.lower() == "water elemental"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
