import pytest
from lib.cardlib import Card
from lib import utils

def test_to_dict_basic_creature():
    card_json = {
        "name": "Grizzly Bears",
        "manaCost": "{1}{G}",
        "types": ["Creature"],
        "subtypes": ["Bear"],
        "rarity": "Common",
        "power": "2",
        "toughness": "2",
        "text": "Whenever Grizzly Bears enters the battlefield, you win."
    }
    card = Card(card_json)
    d = card.to_dict()

    assert d['name'] == "Grizzly Bears"
    assert d['manaCost'] == "{1}{G}"
    assert d['types'] == ["Creature"]
    assert d['subtypes'] == ["Bear"]
    assert d['rarity'] == "common"
    assert d['power'] == "2"
    assert d['toughness'] == "2"
    # Text should be sentence-cased and self-references replaced
    assert d['text'] == "Whenever Grizzly Bears enters the battlefield, you win."

def test_to_dict_planeswalker():
    card_json = {
        "name": "Jace Beleren",
        "manaCost": "{1}{U}{U}",
        "types": ["Planeswalker"],
        "rarity": "Rare",
        "loyalty": 3,
        "text": "+2: Each player draws a card."
    }
    card = Card(card_json)
    d = card.to_dict()

    assert d['loyalty'] == "3"
    assert 'defense' not in d
    assert d['text'] == "+2: Each player draws a card."

def test_to_dict_battle():
    card_json = {
        "name": "Invasion of Zendikar",
        "manaCost": "{3}{G}",
        "types": ["Battle"],
        "rarity": "Uncommon",
        "defense": 3,
        "text": "When Invasion of Zendikar enters the battlefield..."
    }
    card = Card(card_json)
    d = card.to_dict()

    assert d['defense'] == "3"
    assert 'loyalty' not in d

def test_to_dict_split_card():
    # Cardlib handles split cards via 'bside' in JSON
    card_json = {
        "name": "Fire",
        "manaCost": "{1}{R}",
        "types": ["Instant"],
        "rarity": "Uncommon",
        "text": "Fire deals 2 damage divided as you choose among one or two targets.",
        "bside": {
            "name": "Ice",
            "manaCost": "{1}{U}",
            "types": ["Instant"],
            "rarity": "Uncommon",
            "text": "Tap target permanent. Draw a card."
        }
    }
    card = Card(card_json)
    d = card.to_dict()

    assert d['name'] == "Fire"
    assert 'bside' in d
    assert d['bside']['name'] == "Ice"
    assert d['bside']['manaCost'] == "{1}{U}"

def test_to_dict_complex_text():
    card_json = {
        "name": "Promise of Power",
        "manaCost": "{2}{B}{B}{B}",
        "types": ["Sorcery"],
        "rarity": "Rare",
        "text": "Choose one —\n• You draw five cards and you lose 5 life.\n• Create a X/X black Demon creature token with flying, where X is the number of cards in your hand.\nEntwine {4}"
    }
    card = Card(card_json)
    d = card.to_dict()

    # Choice formatting: [Choose one ~ = ... = ...]
    # Note: Entwine might be moved to the top due to linetrans

    expected_text_part = "Choose one ~"
    assert expected_text_part in d['text']
    # Bullet marker should be restored (to whatever it is in config, usually '=')
    assert "=" in d['text']
    assert "Entwine {4}" in d['text']

def test_to_dict_no_rarity():
    card_json = {
        "name": "Token",
        "types": ["Token"]
    }
    # Rarity is required for Card to be parsed=True in fields_from_json
    # Wait, let's check cardlib.py:183
    # if 'rarity' in src_json: ... else: parsed = False
    card = Card(card_json)
    assert not card.parsed
    d = card.to_dict()
    assert d['name'] == "Token"
    assert 'rarity' not in d

def test_to_dict_self_reference():
    card_json = {
        "name": "Grizzly Bears",
        "types": ["Creature"],
        "rarity": "Rare",
        "text": "Whenever Grizzly Bears deals damage, you win."
    }
    # During fields_from_json, "Grizzly Bears" in text is replaced by @.
    # to_dict should restore it.
    card = Card(card_json)
    d = card.to_dict()
    assert "Grizzly Bears" in d['text']
    assert "@" not in d['text']

def test_to_dict_counters():
    # Card with counters in encoded format
    card_text = "|1Gideon|5Planeswalker|7rare|9+1: put a % counter on @. \\ countertype % loyalty"
    card = Card(card_text)
    d = card.to_dict()

    # It should replace % with 'loyalty' and remove the countertype line
    assert "loyalty counter" in d['text']
    assert "%" not in d['text']
    assert "countertype" not in d['text']
