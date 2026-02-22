import os
import sys
import pytest
import tempfile
import json

# Ensure lib is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib import jdecode

def test_advanced_filtering():
    # Setup sample data with set codes and rarities
    cards_data = {
        "data": {
            "MOM": {
                "name": "March of the Machine",
                "code": "MOM",
                "type": "expansion",
                "cards": [
                    {
                        "name": "Fire Dragon",
                        "types": ["Creature"],
                        "power": "5",
                        "toughness": "5",
                        "rarity": "rare",
                        "setCode": "MOM"
                    },
                    {
                        "name": "Water Elemental",
                        "types": ["Creature"],
                        "power": "5",
                        "toughness": "4",
                        "rarity": "uncommon",
                        "setCode": "MOM"
                    }
                ]
            },
            "MRD": {
                "name": "Mirrodin",
                "code": "MRD",
                "type": "expansion",
                "cards": [
                    {
                        "name": "Fireball",
                        "types": ["Sorcery"],
                        "rarity": "uncommon",
                        "setCode": "MRD"
                    },
                    {
                        "name": "Black Lotus",
                        "types": ["Artifact"],
                        "rarity": "rare",
                        "setCode": "MRD"
                    }
                ]
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False, encoding='utf-8') as tmp:
        json.dump(cards_data, tmp)
        tmp_path = tmp.name

    try:
        # Test 1: Filter by set "MOM"
        cards = jdecode.mtg_open_file(tmp_path, sets=["MOM"])
        assert len(cards) == 2
        names = [c.name.lower() for c in cards]
        assert "fire dragon" in names
        assert "water elemental" in names
        assert "fireball" not in names

        # Test 2: Filter by set "MRD"
        cards = jdecode.mtg_open_file(tmp_path, sets=["MRD"])
        assert len(cards) == 2
        names = [c.name.lower() for c in cards]
        assert "fireball" in names
        assert "black lotus" in names

        # Test 3: Filter by rarity "rare"
        cards = jdecode.mtg_open_file(tmp_path, rarities=["rare"])
        assert len(cards) == 2
        names = [c.name.lower() for c in cards]
        assert "fire dragon" in names
        assert "black lotus" in names

        # Test 4: Filter by set "MOM" AND rarity "rare"
        cards = jdecode.mtg_open_file(tmp_path, sets=["MOM"], rarities=["rare"])
        assert len(cards) == 1
        assert cards[0].name.lower() == "fire dragon"

        # Test 5: Filter by multiple sets
        cards = jdecode.mtg_open_file(tmp_path, sets=["MOM", "MRD"])
        assert len(cards) == 4

        # Test 6: Filter by rarity using markers (if known)
        # rare marker is 'A' according to config.py
        cards = jdecode.mtg_open_file(tmp_path, rarities=["A"])
        assert len(cards) == 2
        names = [c.name.lower() for c in cards]
        assert "fire dragon" in names
        assert "black lotus" in names

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
