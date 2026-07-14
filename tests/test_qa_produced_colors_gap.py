import pytest
from lib.cardlib import Card

def test_produced_colors_numeric():
    card = Card({
        "name": "Test Land 1",
        "types": ["Land"],
        "text": "Add 1 white mana."
    })
    assert "W" in card.produced_colors

def test_produced_colors_multiple_numeric():
    card = Card({
        "name": "Test Land 2",
        "types": ["Land"],
        "text": "Add 2 red mana."
    })
    assert "R" in card.produced_colors

def test_produced_colors_number_words():
    card = Card({
        "name": "Test Land 3",
        "types": ["Land"],
        "text": "Add four blue mana."
    })
    assert "U" in card.produced_colors

def test_produced_colors_x():
    card = Card({
        "name": "Test Land 4",
        "types": ["Land"],
        "text": "Add X green mana."
    })
    assert "G" in card.produced_colors

def test_produced_colors_black():
    card = Card({
        "name": "Test Land 5",
        "types": ["Land"],
        "text": "Add 1 black mana."
    })
    assert "B" in card.produced_colors

def test_produced_colors_colorless_numeric():
    card = Card({
        "name": "Test Land 6",
        "types": ["Land"],
        "text": "Add 2 colorless mana."
    })
    assert "C" in card.produced_colors

def test_produced_colors_mixed_styles():
    card = Card({
        "name": "Test Land 7",
        "types": ["Land"],
        "text": "T: Add 1 green mana. Add {R}."
    })
    assert "G" in card.produced_colors
    assert "R" in card.produced_colors
