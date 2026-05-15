import sys
import os
import pytest

# Add lib directory to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

from cardlib import Card

def test_power_rating_tdfc_back_only():
    """
    Verifies that power_rating correctly identifies creature power on the back face
    of a card whose front face is NOT a creature (e.g., a Saga transforming into a creature).
    """
    # Saga that transforms into a creature
    # Front: Not a creature (Enchantment)
    # Back: Creature 2/2 with Flying
    tdfc_json = {
        "name": "The Saga",
        "manaCost": "{1}{G}",
        "types": ["Enchantment", "Saga"],
        "text": "III - Exile this, then return it transformed.",
        "rarity": "rare",
        "bside": {
            "name": "The Spirit",
            "types": ["Creature"],
            "subtypes": ["Spirit"],
            "pt": "&^^/&^^", # 2/2 in unary
            "text": "Flying"
        }
    }

    card = Card(tdfc_json)

    # Assertions
    assert not card.is_creature, "Front face should not be identified as a creature"
    assert card.bside.is_creature, "Back face should be identified as a creature"

    # Back face rating: (2 + 2 + 1.5) / (2 * max(1, 2)) = 5.5 / 4 = 1.375
    # Since Card(tdfc_json) will parse bside as a Card, it shares the front face CMC (2)
    # in some formats, but here it's parsed from JSON.
    # Actually, cardlib.Card constructor for bside uses the provided dictionary.
    # Manacost for bside will be empty if not provided, CMC 0.

    back_rating = card.bside.power_rating
    assert back_rating > 0.0, f"Back face power rating should be positive, got {back_rating}"

    # The overall rating should match the maximum across faces
    assert card.power_rating == back_rating, f"Overall power rating {card.power_rating} should match back face rating {back_rating}"

def test_power_rating_creature_front_only():
    """Verifies that power_rating still works for normal creatures."""
    creature_json = {
        "name": "Grizzly Bears",
        "manaCost": "{1}{G}",
        "types": ["Creature"],
        "subtypes": ["Bear"],
        "pt": "&^^/&^^", # 2/2
        "rarity": "common"
    }
    card = Card(creature_json)
    # (2+2)/(2*2) = 1.0
    assert card.power_rating == 1.0
