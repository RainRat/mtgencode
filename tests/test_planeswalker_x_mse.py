import pytest
from lib.cardlib import Card

def test_planeswalker_x_loyalty_to_mse():
    pw_json = {
        "name": "Nissa, Steward of Elements",
        "manaCost": "{X}{G}{U}",
        "types": ["Planeswalker"],
        "rarity": "Mythic",
        "text": "+X: Scry X.\n-10: You win.",
        "loyalty": "X"
    }
    card = Card(pw_json)
    mse_output = card.to_mse()

    assert "loyalty cost 1: +X" in mse_output
    assert "loyalty cost 2: -10" in mse_output
    assert "\trule text:\n\t\tScry X.\n\t\tYou win." in mse_output

def test_planeswalker_lowercase_x_loyalty_to_mse():
    pw_json = {
        "name": "Test Walker",
        "manaCost": "{1}{R}",
        "types": ["Planeswalker"],
        "rarity": "Rare",
        "text": "+x: Damage.\n-1: Draw.",
        "loyalty": 2
    }
    card = Card(pw_json)
    mse_output = card.to_mse()

    assert "loyalty cost 1: +X" in mse_output
    assert "\trule text:\n\t\tDamage.\n\t\tDraw." in mse_output
