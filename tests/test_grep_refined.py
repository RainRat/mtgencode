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

def test_grep_name(sample_cards_file):
    # Should only match Fire Dragon and Fireball, NOT Water Elemental (which might match if we searched everything)
    cards = jdecode.mtg_open_file(sample_cards_file, grep_name=["Fire"])
    assert len(cards) == 2
    names = [c.name for c in cards]
    assert "fire dragon" in names
    assert "fireball" in names
    assert "water elemental" not in names

def test_grep_type(sample_cards_file):
    # Should match Fire Dragon and Water Elemental
    cards = jdecode.mtg_open_file(sample_cards_file, grep_types=["Creature"])
    assert len(cards) == 2
    names = [c.name for c in cards]
    assert "fire dragon" in names
    assert "water elemental" in names

    # Should match Fire Dragon (Dragon subtype)
    cards = jdecode.mtg_open_file(sample_cards_file, grep_types=["Dragon"])
    assert len(cards) == 1
    assert cards[0].name == "fire dragon"

def test_grep_text(sample_cards_file):
    # Should match Water Elemental (Islandwalk)
    cards = jdecode.mtg_open_file(sample_cards_file, grep_text=["Islandwalk"])
    assert len(cards) == 1
    assert cards[0].name == "water elemental"

    # Should match Fire Dragon and Fireball (deals damage)
    cards = jdecode.mtg_open_file(sample_cards_file, grep_text=["deals"])
    assert len(cards) == 2
    names = [c.name for c in cards]
    assert "fire dragon" in names
    assert "fireball" in names

def test_exclude_name(sample_cards_file):
    # Exclude cards with "Fire" in name
    cards = jdecode.mtg_open_file(sample_cards_file, vgrep_name=["Fire"])
    assert len(cards) == 2
    names = [c.name for c in cards]
    assert "water elemental" in names
    assert "island" in names
    assert "fire dragon" not in names
    assert "fireball" not in names

def test_exclude_type(sample_cards_file):
    # Exclude Creatures
    cards = jdecode.mtg_open_file(sample_cards_file, vgrep_types=["Creature"])
    assert len(cards) == 2
    names = [c.name for c in cards]
    assert "fireball" in names
    assert "island" in names
    assert "fire dragon" not in names

def test_exclude_text(sample_cards_file):
    # Exclude cards that deal damage
    cards = jdecode.mtg_open_file(sample_cards_file, vgrep_text=["deals"])
    assert len(cards) == 2
    names = [c.name for c in cards]
    assert "water elemental" in names
    assert "island" in names

def test_combined_filters(sample_cards_file):
    # Name contains "Fire" AND type is "Sorcery"
    cards = jdecode.mtg_open_file(sample_cards_file, grep_name=["Fire"], grep_types=["Sorcery"])
    assert len(cards) == 1
    assert cards[0].name == "fireball"

    # Type is "Creature" AND text DOES NOT contain "Flying"
    cards = jdecode.mtg_open_file(sample_cards_file, grep_types=["Creature"], vgrep_text=["Flying"])
    assert len(cards) == 1
    assert cards[0].name == "water elemental"
