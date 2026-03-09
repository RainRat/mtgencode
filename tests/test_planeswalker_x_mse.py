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

def test_non_planeswalker_substring_not_planeswalker_to_mse():
    # Verify that types containing 'planeswalker' as a substring but not as a whole word
    # do not trigger planeswalker-specific logic in to_mse()
    card_json = {
        "name": "Not a Walker",
        "manaCost": "{2}{G}",
        "types": ["Not Planeswalker"],
        "rarity": "Common",
        "text": "This is just a card."
    }
    card = Card(card_json)
    mse_output = card.to_mse()

    # Should NOT have the planeswalker stylesheet
    assert "stylesheet: m15-planeswalker" not in mse_output
    # Should NOT have loyalty cost fields
    assert "loyalty cost" not in mse_output
    # Should have the rule text formatted normally
    assert "\trule text:\n\t\tThis is just a card." in mse_output
