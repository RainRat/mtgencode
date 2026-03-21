import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lib.cardlib import Card

def test_mechanics_token_singular():
    card_json = {
        "name": "Token Generator",
        "types": ["Sorcery"],
        "text": "Create a 1/1 white Soldier creature token.",
        "rarity": "Common"
    }
    card = Card(card_json)
    assert 'Token' in card.mechanics

def test_mechanics_token_plural():
    card_json = {
        "name": "Tokens Generator",
        "types": ["Sorcery"],
        "text": "Create two 1/1 white Soldier creature tokens.",
        "rarity": "Common"
    }
    card = Card(card_json)
    assert 'Token' in card.mechanics
