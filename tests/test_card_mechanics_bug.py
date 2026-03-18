import sys
import os

# Ensure lib is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib')))

from cardlib import Card

def test_x_cost_false_positive():
    # "Exile" contains 'x', which shouldn't trigger 'X-Cost/Effect'
    card = Card({
        "name": "Exile Test",
        "manaCost": "{1}{W}",
        "types": ["Instant"],
        "text": "Exile target creature.",
        "rarity": "common"
    })
    # Currently, this will FAIL because 'X-Cost/Effect' is incorrectly added
    assert 'X-Cost/Effect' not in card.mechanics

def test_x_cost_true_positive():
    # Standalone 'X' should trigger 'X-Cost/Effect'
    card = Card({
        "name": "Fireball",
        "manaCost": "{X}{R}",
        "types": ["Sorcery"],
        "text": "Fireball deals X damage to any target.",
        "rarity": "uncommon"
    })
    assert 'X-Cost/Effect' in card.mechanics

def test_kicker():
    card = Card({"name": "T", "types": ["Instant"], "text": "Kicker {1}", "rarity": "common"})
    assert 'Kicker' in card.mechanics

def test_uncast():
    # Use a name that doesn't conflict with 'target' or 'spell' for replacement
    card = Card({"name": "Test Name", "types": ["Instant"], "text": "Uncast target spell.", "rarity": "common"})
    assert 'Uncast' in card.mechanics

def test_equipment_by_subtype():
    card = Card({"name": "Test Name", "types": ["Artifact"], "subtypes": ["Equipment"], "text": "Equip {1}", "rarity": "common"})
    assert 'Equipment' in card.mechanics

def test_leveler():
    card = Card({"name": "Test Name", "types": ["Creature"], "text": "Level up {1}", "rarity": "common", "pt": "1/1"})
    assert 'Leveler' in card.mechanics

def test_counters_by_marker():
    # % is counter_marker
    card = Card({"name": "Test Name", "types": ["Artifact"], "text": "Put a % counter on @.", "rarity": "common"})
    assert 'Counters' in card.mechanics

def test_counters_by_number_marker():
    # # is also used for counters in some contexts (unary conversion)
    # Actually # is not a standard marker in config.py, but it was in the code.
    # Let's check what triggers it.
    card = Card({"name": "Test Name", "types": ["Artifact"], "text": "Put # counters on @.", "rarity": "common"})
    assert 'Counters' in card.mechanics
