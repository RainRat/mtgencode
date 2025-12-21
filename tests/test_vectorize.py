import pytest
import random
from lib.cardlib import Card
from lib import utils

def test_vectorize_creature():
    card_data = {
        "name": "Test Creature",
        "manaCost": "{G}",
        "type": "Creature — Elf",
        "types": ["Creature"],
        "subtypes": ["Elf"],
        "rarity": "Common",
        "text": "Trample",
        "power": "2",
        "toughness": "2"
    }
    card = Card(card_data)
    vectorized = card.vectorize()

    # Common -> O (as per config.rarity_common_marker)
    assert "(O)" in vectorized
    # Types lowercased and wrapped
    assert "(creature)" in vectorized
    # Subtypes are just appended
    assert "elf" in vectorized

    # P/T processing
    # 2 -> &^^
    unary_2 = utils.to_unary("2")
    # Actual behavior in codebase: replace('/', '/ /') results in "A/ /B", splitting to "A/" and "/B"
    # So we expect (&^^/) (/&^^)
    # The split items are wrapped in parens and joined by space.
    expected_pt_part = f"({unary_2}/) (/{unary_2})"
    assert expected_pt_part in vectorized

def test_vectorize_planeswalker():
    card_data = {
        "name": "Test PW",
        "manaCost": "{1}{W}",
        "type": "Legendary Planeswalker — Test",
        "types": ["Planeswalker"],
        "subtypes": ["Test"],
        "rarity": "Mythic",
        "text": "+1: Gain life.",
        "loyalty": "4"
    }
    card = Card(card_data)
    vectorized = card.vectorize()

    # Mythic -> Y
    assert "(Y)" in vectorized

    # Loyalty for non-battle: ((value))
    unary_4 = utils.to_unary("4")
    assert f"(({unary_4}))" in vectorized

def test_vectorize_battle():
    card_data = {
        "name": "Test Battle",
        "manaCost": "{R}",
        "type": "Battle — Siege",
        "types": ["Battle"],
        "subtypes": ["Siege"],
        "rarity": "Rare",
        "text": "Burn stuff.",
        "defense": "5"
    }
    card = Card(card_data)
    vectorized = card.vectorize()

    # Rare -> A
    assert "(A)" in vectorized

    # Loyalty for battle: [[value]]
    unary_5 = utils.to_unary("5")
    assert f"[[{unary_5}]]" in vectorized

def test_encode_randomization():
    card_data = {
        "name": "Chaotic Card",
        "manaCost": "{G}{U}", # Two mana symbols
        "type": "Instant",
        "types": ["Instant"],
        "text": "Effect 1.\nEffect 2."
    }
    card = Card(card_data)

    # Test randomize_mana
    # {G}{U} -> could be {U}{G}
    # Run multiple times to ensure we see a change
    variants = set()
    # We need enough trials to be statistically nearly certain to see both
    # Probability of same result 20 times is 0.5^19 (very low)
    for _ in range(20):
        encoded = card.encode(randomize_mana=True)
        variants.add(encoded)

    assert len(variants) > 1, "randomize_mana did not produce variations"

    # Test randomize_lines
    variants = set()
    for _ in range(20):
        encoded = card.encode(randomize_lines=True)
        variants.add(encoded)
    assert len(variants) > 1, "randomize_lines did not produce variations"

def test_encode_randomize_fields():
    card_data = {
        "name": "Chaotic Fields",
        "type": "Sorcery",
        "types": ["Sorcery"],
        "text": "Chaos."
    }
    card = Card(card_data)

    variants = set()
    for _ in range(20):
        encoded = card.encode(randomize_fields=True)
        variants.add(encoded)

    assert len(variants) > 1, "randomize_fields did not produce variations"
