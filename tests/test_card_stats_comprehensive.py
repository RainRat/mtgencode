import pytest
import sys
import os

# Ensure lib is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lib.cardlib import Card
from lib import utils

@pytest.fixture
def creature_json():
    return {
        "name": "Grizzly Bears",
        "manaCost": "{1}{G}",
        "types": ["Creature"],
        "subtypes": ["Bear"],
        "rarity": "Common",
        "power": "2",
        "toughness": "2",
        "text": "Vanilla."
    }

@pytest.fixture
def planeswalker_json():
    return {
        "name": "Jace Beleren",
        "manaCost": "{1}{U}{U}",
        "types": ["Planeswalker"],
        "subtypes": ["Jace"],
        "rarity": "Rare",
        "loyalty": "3",
        "text": "+2: Draw."
    }

@pytest.fixture
def battle_json():
    return {
        "name": "Invasion of Zendikar",
        "manaCost": "{3}{G}",
        "types": ["Battle"],
        "subtypes": ["Siege"],
        "rarity": "Uncommon",
        "defense": "3",
        "text": "ETB: Search."
    }

def test_type_properties(creature_json, planeswalker_json, battle_json):
    creature = Card(creature_json)
    assert creature.is_creature
    assert not creature.is_planeswalker
    assert not creature.is_battle

    pw = Card(planeswalker_json)
    assert not pw.is_creature
    assert pw.is_planeswalker
    assert not pw.is_battle

    battle = Card(battle_json)
    assert not battle.is_creature
    assert not battle.is_planeswalker
    assert battle.is_battle

def test_stat_display_summary(creature_json, planeswalker_json, battle_json):
    creature = Card(creature_json)
    assert "• (2/2)" in creature.summary()

    pw = Card(planeswalker_json)
    assert "• (3)" in pw.summary()

    battle = Card(battle_json)
    assert "• [[3]]" in battle.summary()

def test_stat_display_format_default(creature_json, planeswalker_json, battle_json):
    creature = Card(creature_json)
    assert "\n(2/2)" in creature.format()

    pw = Card(planeswalker_json)
    assert "\n((3))" in pw.format()

    battle = Card(battle_json)
    assert "\n[[3]]" in battle.format()

def test_stat_display_format_gatherer(creature_json, planeswalker_json, battle_json):
    creature = Card(creature_json)
    assert " — Bear (2/2)" in creature.format(gatherer=True)

    pw = Card(planeswalker_json)
    assert " — Jace ((3))" in pw.format(gatherer=True)

    battle = Card(battle_json)
    assert " — Siege [[3]]" in battle.format(gatherer=True)

def test_stat_display_to_dict(creature_json, planeswalker_json, battle_json):
    creature = Card(creature_json)
    d = creature.to_dict()
    assert d["power"] == "2"
    assert d["toughness"] == "2"

    pw = Card(planeswalker_json)
    d = pw.to_dict()
    assert d["loyalty"] == "3"
    assert "defense" not in d

    battle = Card(battle_json)
    d = battle.to_dict()
    assert d["defense"] == "3"
    assert "loyalty" not in d

def test_stat_display_to_markdown_row(creature_json, planeswalker_json, battle_json):
    creature = Card(creature_json)
    assert "| 2/2 |" in creature.to_markdown_row()

    pw = Card(planeswalker_json)
    assert "| (3) |" in pw.to_markdown_row()

    battle = Card(battle_json)
    assert "| [[3]] |" in battle.to_markdown_row()

def test_stat_display_vectorize(creature_json, planeswalker_json, battle_json):
    creature = Card(creature_json)
    v = creature.vectorize()
    # 2/2 -> (&^^/) (/&^^)
    assert "(&^^/) (/&^^)" in v

    pw = Card(planeswalker_json)
    v = pw.vectorize()
    assert "((&^^^))" in v

    battle = Card(battle_json)
    v = battle.vectorize()
    assert "[[&^^^]]" in v

def test_ansi_colors_stats(creature_json, planeswalker_json, battle_json):
    red = utils.Ansi.RED
    reset = utils.Ansi.RESET

    creature = Card(creature_json)
    summary = creature.summary(ansi_color=True)
    assert f"{red}(2/2){reset}" in summary

    pw = Card(planeswalker_json)
    summary = pw.summary(ansi_color=True)
    assert f"{red}(3){reset}" in summary

    battle = Card(battle_json)
    summary = battle.summary(ansi_color=True)
    assert f"{red}[[3]]{reset}" in summary

def test_is_creature_vehicle():
    vehicle_json = {
        "name": "Smuggler's Copter",
        "types": ["Artifact"],
        "subtypes": ["Vehicle"],
        "pt": "3/3"
    }
    card = Card(vehicle_json)
    assert card.is_creature
    assert card.is_artifact
