import pytest
import re
from lib.cardlib import Card

def test_search_rarity_by_human_readable_name():
    card = Card({
        "name": "Rare Card",
        "types": ["Creature"],
        "rarity": "Rare"
    })
    assert card.search(re.compile(r"rare", re.IGNORECASE))
    assert card.search_rarity(re.compile(r"rare", re.IGNORECASE))

def test_search_rarity_by_internal_marker():
    card = Card({
        "name": "Rare Card",
        "types": ["Creature"],
        "rarity": "Rare"
    })
    assert card.search_rarity(re.compile(r"A"))

def test_search_multi_word_type_line_spanning_supertypes_and_types():
    card = Card({
        "name": "Thrun, the Last Troll",
        "supertypes": ["Legendary"],
        "types": ["Creature"],
        "subtypes": ["Troll", "Shaman"],
        "rarity": "Rare"
    })
    assert card.search_types(re.compile(r"Legendary Creature", re.IGNORECASE))

def test_search_multi_word_subtypes():
    card = Card({
        "name": "Thrun, the Last Troll",
        "supertypes": ["Legendary"],
        "types": ["Creature"],
        "subtypes": ["Troll", "Shaman"],
        "rarity": "Rare"
    })
    assert card.search_types(re.compile(r"Troll Shaman", re.IGNORECASE))

def test_search_rarity_recursive_bside():
    card = Card({
        "name": "Front",
        "types": ["Instant"],
        "rarity": "Uncommon",
        "bside": {
            "name": "Back",
            "types": ["Sorcery"],
            "rarity": "Rare"
        }
    })
    assert card.search_rarity(re.compile(r"rare", re.IGNORECASE))

def test_search_types_recursive_bside():
    card = Card({
        "name": "Front",
        "types": ["Instant"],
        "rarity": "Common",
        "bside": {
            "name": "Back",
            "types": ["Creature"],
            "subtypes": ["Zombie"],
            "rarity": "Common"
        }
    })
    assert card.search_types(re.compile(r"Zombie", re.IGNORECASE))
