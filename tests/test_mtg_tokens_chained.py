import pytest
from lib.cardlib import Card

def test_chained_token_creation():
    """Verify that multiple tokens created in a single sentence are correctly identified."""
    card_json = {
        "name": "Multi Token Generator",
        "manaCost": "{4}{W}{G}",
        "types": ["Sorcery"],
        "text": "Create two 1/1 white Soldier creature tokens and a 4/4 green Rhino creature token with trample.",
        "rarity": "rare"
    }
    card = Card(card_json)
    tokens = card.tokens
    token_names = [t['name'] for t in tokens]

    assert len(tokens) == 2
    assert "1/1 White Soldier Token" in token_names
    assert "4/4 Green Rhino Token" in token_names

    # Verify rhino properties
    rhino = next(t for t in tokens if "Rhino" in t['name'])
    assert rhino['pt'] == "4/4"
    assert rhino['color'] == "Green"
    assert rhino['abilities'] == "trample"

def test_chained_token_creation_case_variation():
    """Verify robust handling of 'and' with different casing."""
    card_json = {
        "name": "Another Generator",
        "types": ["Sorcery"],
        "text": "Create a 1/1 white Spirit creature token with flying AND a 1/1 colorless Spirit creature token.",
        "rarity": "uncommon"
    }
    card = Card(card_json)
    token_names = [t['name'] for t in card.tokens]
    assert "1/1 White Spirit Token" in token_names
    assert "1/1 Colorless Spirit Token" in token_names
