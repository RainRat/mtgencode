import pytest
import sys
import os

# Ensure lib is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lib.cardlib import Card
from lib import utils

def test_mechanics_keyword_as_name():
    """Verify that keywords are identified even when the card name is the keyword."""
    # Test 'Exile' (Alliances)
    exile_card = Card({
        "name": "Exile",
        "manaCost": "{2}{W}",
        "types": ["Instant"],
        "text": "Exile target nonwhite attacking creature. You gain life equal to its toughness.",
        "rarity": "Rare"
    })
    assert 'Exile' in exile_card.mechanics

    # Test 'Flying'
    flying_card = Card({
        "name": "Flying",
        "types": ["Creature"],
        "text": "Flying",
        "rarity": "Common",
        "power": "1",
        "toughness": "1"
    })
    assert 'Flying' in flying_card.mechanics

def test_mechanics_keyword_in_name_collision_prevention():
    """Verify that we don't get false positives for keywords when they are part of a longer name."""
    # A card named "Trample Bear" should not have "Trample" just because of its name.
    # The name replacement results in "trample_bear" which should NOT match "\btrample\b".
    trample_bear = Card({
        "name": "Trample Bear",
        "types": ["Creature"],
        "text": "When @ enters the battlefield, do nothing.",
        "rarity": "Common",
        "power": "2",
        "toughness": "2"
    })
    assert 'Trample' not in trample_bear.mechanics
    assert 'ETB Effect' in trample_bear.mechanics

def test_rarity_parsing_case_robustness():
    """Verify that rarity parsing is case-insensitive and handles 'basic land'."""
    # Test lowercase basic land
    basic_land_lower = Card({
        "name": "Plains",
        "types": ["Land"],
        "rarity": "basic land"
    })
    assert basic_land_lower.rarity == utils.rarity_basic_land_marker
    assert basic_land_lower.parsed

    # Test mixed case rarity
    mythic_mixed = Card({
        "name": "Mixed Mythic",
        "types": ["Sorcery"],
        "rarity": "mYtHiC rArE"
    })
    assert mythic_mixed.rarity == utils.rarity_mythic_marker
    assert mythic_mixed.parsed

def test_mechanics_triggered_as_name():
    """Verify that trigger keywords are identified even when the card name is the trigger word."""
    at_card = Card({
        "name": "At",
        "types": ["Enchantment"],
        "text": "At the beginning of your upkeep, win.",
        "rarity": "Rare"
    })
    # The text becomes "@ the beginning of your upkeep, win."
    # Our fix ensures line.startswith('at ') works because line is @-replaced.
    assert 'Triggered' in at_card.mechanics
