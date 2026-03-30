from lib.cardlib import Card

def test_type_properties_case_insensitivity():
    # Create a card with mixed-case types
    card_json = {
        "name": "Mixed Case Card",
        "types": ["Creature", "Artifact"],
        "subtypes": ["Vehicle"]
    }
    card = Card(card_json)

    # In this project, Card initialization from JSON currently converts types to lowercase
    # So we should also test by manually setting types to mixed case
    card.types = ["Creature", "Artifact"]
    card.subtypes = ["Vehicle"]

    assert card.is_creature
    assert card.is_artifact
    assert not card.is_land

    card.types = ["Land"]
    card.subtypes = [] # Clear subtypes
    assert card.is_land
    assert not card.is_creature

    card.types = ["Instant"]
    assert card.is_instant

    card.types = ["Sorcery"]
    assert card.is_sorcery

    card.types = ["Planeswalker"]
    assert card.is_planeswalker

    card.types = ["Battle"]
    assert card.is_battle

    card.types = ["Enchantment"]
    assert card.is_enchantment
