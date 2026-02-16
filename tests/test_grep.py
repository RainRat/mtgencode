import os
import sys
import pytest
import tempfile
import json

# Ensure lib is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib import jdecode, cardlib

def test_grep_filtering():
    # Setup sample data
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
        }
    ]

    with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False, encoding='utf-8') as tmp:
        json.dump(cards_data, tmp)
        tmp_path = tmp.name

    try:
        # Test 1: Grep for "Dragon"
        cards = jdecode.mtg_open_file(tmp_path, grep=["Dragon"])
        assert len(cards) == 1
        assert cards[0].name == "fire dragon"

        # Test 2: Grep for "Fire"
        cards = jdecode.mtg_open_file(tmp_path, grep=["Fire"])
        assert len(cards) == 2
        names = [c.name for c in cards]
        assert "fire dragon" in names
        assert "fireball" in names

        # Test 3: Multiple greps (AND logic) - "Fire" and "Dragon"
        cards = jdecode.mtg_open_file(tmp_path, grep=["Fire", "Dragon"])
        assert len(cards) == 1
        assert cards[0].name == "fire dragon"

        # Test 4: Grep for something that doesn't exist
        cards = jdecode.mtg_open_file(tmp_path, grep=["Zombie"])
        assert len(cards) == 0

        # Test 5: Grep by rules text
        cards = jdecode.mtg_open_file(tmp_path, grep=["Islandwalk"])
        assert len(cards) == 1
        assert cards[0].name == "water elemental"

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_vgrep_filtering():
    # Setup sample data
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
        }
    ]

    with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False, encoding='utf-8') as tmp:
        json.dump(cards_data, tmp)
        tmp_path = tmp.name

    try:
        # Test 1: Vgrep for "Dragon" - should exclude Fire Dragon
        cards = jdecode.mtg_open_file(tmp_path, vgrep=["Dragon"])
        assert len(cards) == 2
        names = [c.name for c in cards]
        assert "fire dragon" not in names
        assert "water elemental" in names
        assert "fireball" in names

        # Test 2: Vgrep for "Fire" - should exclude Fire Dragon and Fireball
        cards = jdecode.mtg_open_file(tmp_path, vgrep=["Fire"])
        assert len(cards) == 1
        assert cards[0].name == "water elemental"

        # Test 3: Multiple vgreps (OR logic) - exclude "Dragon" or "Elemental"
        cards = jdecode.mtg_open_file(tmp_path, vgrep=["Dragon", "Elemental"])
        assert len(cards) == 1
        assert cards[0].name == "fireball"

        # Test 4: Combine grep and vgrep - "Fire" but not "Sorcery"
        cards = jdecode.mtg_open_file(tmp_path, grep=["Fire"], vgrep=["Sorcery"])
        assert len(cards) == 1
        assert cards[0].name == "fire dragon"

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_grep_encoded_text():
    # Setup sample encoded data
    encoded_text = (
        "|1Fire Dragon|5Creature|6Dragon|3{4}{R}{R}|7rare|85/5|9Flying\\{R}: Fire Dragon deals 1 damage.\n\n"
        "|1Water Elemental|5Creature|6Elemental|3{3}{U}{U}|7uncommon|85/4|9Islandwalk\n\n"
    )

    with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False, encoding='utf-8') as tmp:
        tmp.write(encoded_text)
        tmp_path = tmp.name

    try:
        # Test 1: Grep for "Elemental"
        cards = jdecode.mtg_open_file(tmp_path, grep=["Elemental"])
        assert len(cards) == 1
        assert cards[0].name.lower() == "water elemental"

        # Test 2: Grep for "Flying"
        cards = jdecode.mtg_open_file(tmp_path, grep=["Flying"])
        assert len(cards) == 1
        assert cards[0].name.lower() == "fire dragon"

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
