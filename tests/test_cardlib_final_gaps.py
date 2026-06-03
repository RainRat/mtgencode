import pytest
from lib.cardlib import Card, cap

def test_cap_empty_string():
    assert cap("") == ""

def test_card_actions_with_bside_recursion():
    card_json = {
        "name": "Side A",
        "types": ["Instant"],
        "rarity": "Common",
        "text": "Destroy target creature.",
        "bside": {
            "name": "Side B",
            "types": ["Instant"],
            "text": "Draw a card."
        }
    }
    card = Card(card_json)
    actions = card.actions
    assert "Removal" in actions
    assert "Card Advantage" in actions

def test_card_header_with_bside_recursion():
    card_json = {
        "name": "Side A",
        "types": ["Land"],
        "rarity": "Common",
        "bside": {
            "name": "Side B",
            "types": ["Land"],
            "rarity": "Common"
        }
    }
    card = Card(card_json)
    header = card.header()
    assert "Side A" in header
    assert "Side B" in header
    assert " // " in header

def test_card_summary_functional_actions_ansi():
    card_json = {
        "name": "Murder",
        "manaCost": "{1}{B}{B}",
        "types": ["Instant"],
        "rarity": "Common",
        "text": "Destroy target creature."
    }
    card = Card(card_json)
    summary = card.summary(ansi_color=True)
    assert "Removal" in summary
    assert "\033[" in summary

def test_card_to_dict_includes_produced_colors():
    card_json = {
        "name": "Mountain",
        "types": ["Land"],
        "subtypes": ["Mountain"],
        "rarity": "Basic Land"
    }
    card = Card(card_json)
    d = card.to_dict()
    assert "producedColors" in d
    assert "R" in d["producedColors"]

def test_card_cap_with_special_markers():
    # @ is this_marker, \v is reserved_marker
    assert cap("@") == "@"
    assert cap("\v") == "\v"

def test_card_summary_creature_fair_mv_ansi():
    card_json = {
        "name": "Bear",
        "manaCost": "{1}{G}",
        "types": ["Creature"],
        "power": "2",
        "toughness": "2",
        "rarity": "Common"
    }
    card = Card(card_json)
    summary = card.summary(ansi_color=True)
    assert "Fair MV" in summary
    assert "\033[" in summary
