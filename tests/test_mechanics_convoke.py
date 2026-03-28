import sys
import os

# Ensure lib is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lib.cardlib import Card

def test_mechanics_convoke_keyword():
    """Verify that 'Convoke' is identified as a keyword ability."""
    card = Card({
        "name": "Chord of Calling",
        "manaCost": "{X}{G}{G}{G}",
        "types": ["Instant"],
        "text": "Convoke\nSearch your library for a creature card with mana value X or less and put it onto the battlefield. Then shuffle.",
        "rarity": "Rare"
    })
    assert 'Convoke' in card.mechanics

def test_mechanics_convoke_boundary():
    """Verify that 'Convoke' does not match partial words like 'Convoker'."""
    card = Card({
        "name": "Convoker",
        "types": ["Creature"],
        "text": "A convoker of souls.",
        "rarity": "Common",
        "power": "1",
        "toughness": "1"
    })
    assert 'Convoke' not in card.mechanics

def test_mechanics_convoke_case_insensitive():
    """Verify that 'convoke' is identified regardless of case."""
    card = Card({
        "name": "Case Test",
        "types": ["Instant"],
        "text": "some text with convoke here.",
        "rarity": "Common"
    })
    assert 'Convoke' in card.mechanics
