import pytest
import re
from lib.cardlib import Card

@pytest.fixture
def grizzly_bears():
    return Card({
        "name": "Grizzly Bears",
        "manaCost": "{1}{G}",
        "types": ["Creature"],
        "subtypes": ["Bear"],
        "rarity": "common",
        "power": "2",
        "toughness": "2"
    })

@pytest.fixture
def thrun():
    return Card({
        "name": "Thrun, the Last Troll",
        "manaCost": "{2}{G}{G}",
        "supertypes": ["Legendary"],
        "types": ["Creature"],
        "subtypes": ["Troll", "Shaman"],
        "rarity": "rare",
        "text": "This spell can't be countered.\nHexproof\n{1}{G}: Regenerate Thrun, the Last Troll.",
        "power": "4",
        "toughness": "4"
    })

def test_search_rarity_enhanced(grizzly_bears, thrun):
    # Test internal code (this codebase uses O for common, A for rare)
    assert grizzly_bears.search_rarity(re.compile(r"O"))
    assert thrun.search_rarity(re.compile(r"A"))

    # Test human-readable name via rarity_name
    assert grizzly_bears.search_rarity(re.compile(r"common", re.IGNORECASE))
    assert thrun.search_rarity(re.compile(r"rare", re.IGNORECASE))

def test_search_types_enhanced(thrun):
    # Old behavior (individual elements) still works
    assert thrun.search_types(re.compile(r"Legendary", re.IGNORECASE))
    assert thrun.search_types(re.compile(r"Creature", re.IGNORECASE))
    assert thrun.search_types(re.compile(r"Troll", re.IGNORECASE))

    # New behavior (multi-word type line)
    assert thrun.search_types(re.compile(r"Legendary Creature", re.IGNORECASE))
    assert thrun.search_types(re.compile(r"Troll Shaman", re.IGNORECASE))
    assert thrun.search_types(re.compile(r"Legendary Creature . Troll", re.IGNORECASE))

def test_search_mechanics_enhanced(thrun):
    # Mechanics identified by get_face_mechanics()
    assert thrun.search_mechanics(re.compile(r"Hexproof", re.IGNORECASE))
    assert thrun.search_mechanics(re.compile(r"Activated", re.IGNORECASE)) # {1}{G}: ...

def test_search_actions_enhanced(thrun):
    # Actions identified by get_face_actions()
    assert thrun.search_actions(re.compile(r"Protection", re.IGNORECASE)) # Hexproof is in Protection category
    assert thrun.search_actions(re.compile(r"Mana", re.IGNORECASE)) == False # Thrun doesn't produce mana

def test_search_aggregate_enhanced(thrun):
    # Verify Card.search incorporates new methods
    assert thrun.search(re.compile(r"rare", re.IGNORECASE))
    assert thrun.search(re.compile(r"Hexproof", re.IGNORECASE))
    assert thrun.search(re.compile(r"Protection", re.IGNORECASE))
    assert thrun.search(re.compile(r"Legendary Creature", re.IGNORECASE))
