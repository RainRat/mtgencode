import pytest
from lib.cardlib import Card

def test_white_flash_no_break():
    # Test that White cards with Flash are no longer flagged as breaks
    card_json = {
        "name": "White Flash Creature",
        "manaCost": "{1}{W}",
        "types": ["Creature"],
        "power": "&^^",
        "toughness": "&^^",
        "text": "Flash"
    }
    card = Card(card_json)
    assert card.check_color_pie() is True

def test_black_red_ward_no_break():
    # Black card with Ward
    card_b = Card({
        "name": "Black Ward",
        "manaCost": "{B}",
        "types": ["Creature"],
        "power": "&^",
        "toughness": "&^",
        "text": "Ward {2}"
    })
    assert card_b.check_color_pie() is True

    # Red card with Ward
    card_r = Card({
        "name": "Red Ward",
        "manaCost": "{R}",
        "types": ["Creature"],
        "power": "&^",
        "toughness": "&^",
        "text": "Ward {1}"
    })
    assert card_r.check_color_pie() is True

def test_red_mana_ritual_no_break():
    # Red card with mana ritual
    card = Card({
        "name": "Red Ritual",
        "manaCost": "{R}",
        "types": ["Sorcery"],
        "text": "Add {R}{R}{R}."
    })
    assert "Mana" in card.actions
    assert card.check_color_pie() is True

def test_neg_n_removal_detection():
    # Card with -N/-N effect should be identified as Removal
    card = Card({
        "name": "Death's Caress",
        "manaCost": "{B}",
        "types": ["Instant"],
        "text": "Target creature gets -&^^/-&^^ until end of turn."
    })
    assert "Removal" in card.actions
    assert card.check_color_pie() is True

def test_colorless_no_incorrect_flag():
    # Artifact with standard mechanic
    card = Card({
        "name": "Steel Wall",
        "manaCost": "{1}",
        "types": ["Artifact", "Creature"],
        "power": "0",
        "toughness": "4",
        "text": "Defender"
    })
    # Identity is 'C'. Defender allows 'C'.
    assert card.check_color_pie() is True

    card_flying = Card({
        "name": "Flying Thopter",
        "manaCost": "{2}",
        "types": ["Artifact", "Creature"],
        "power": "1",
        "toughness": "1",
        "text": "Flying"
    })
    # Flying allows 'C'.
    assert card_flying.check_color_pie() is True
