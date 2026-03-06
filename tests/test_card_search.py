import pytest
import re
from lib.cardlib import Card

@pytest.fixture
def simple_card():
    return Card({
        "name": "Grizzly Bears",
        "manaCost": "{1}{G}",
        "types": ["Creature"],
        "subtypes": ["Bear"],
        "rarity": "Common",
        "power": "2",
        "toughness": "2",
        "text": "When Grizzly Bears enters the battlefield, you win."
    })

@pytest.fixture
def split_card():
    return Card({
        "name": "Fire",
        "manaCost": "{1}{R}",
        "types": ["Instant"],
        "rarity": "Uncommon",
        "text": "Fire deals 2 damage.",
        "bside": {
            "name": "Ice",
            "manaCost": "{1}{U}",
            "types": ["Instant"],
            "rarity": "Uncommon",
            "text": "Tap target permanent. Draw a card."
        }
    })

@pytest.fixture
def planeswalker_card():
    return Card({
        "name": "Jace Beleren",
        "manaCost": "{1}{U}{U}",
        "types": ["Planeswalker"],
        "rarity": "Rare",
        "loyalty": 3,
        "text": "+2: Each player draws a card."
    })

def test_search_name(simple_card, split_card):
    pattern = re.compile(r"grizzly", re.IGNORECASE)
    assert simple_card.search_name(pattern)

    pattern = re.compile(r"ice", re.IGNORECASE)
    assert split_card.search_name(pattern)

    pattern = re.compile(r"fire", re.IGNORECASE)
    assert split_card.search_name(pattern)

    pattern = re.compile(r"nomatch")
    assert not simple_card.search_name(pattern)

def test_search_types(simple_card, split_card):
    # simple card
    assert simple_card.search_types(re.compile(r"creature", re.IGNORECASE))
    assert simple_card.search_types(re.compile(r"bear", re.IGNORECASE))

    # split card
    assert split_card.search_types(re.compile(r"instant", re.IGNORECASE))

    # supertype
    legendary_card = Card({"name": "Thrun", "supertypes": ["Legendary"], "types": ["Creature"], "rarity": "Rare"})
    assert legendary_card.search_types(re.compile(r"legendary", re.IGNORECASE))

    assert not simple_card.search_types(re.compile(r"artifact", re.IGNORECASE))

def test_search_text(simple_card, split_card):
    assert simple_card.search_text(re.compile(r"battlefield", re.IGNORECASE))
    assert split_card.search_text(re.compile(r"damage", re.IGNORECASE))
    assert split_card.search_text(re.compile(r"draw", re.IGNORECASE))

    assert not simple_card.search_text(re.compile(r"nomatch"))

def test_search_cost(simple_card, split_card):
    assert simple_card.search_cost(re.compile(re.escape("{1}{G}")))
    assert split_card.search_cost(re.compile(re.escape("{1}{R}")))
    assert split_card.search_cost(re.compile(re.escape("{1}{U}")))

    assert not simple_card.search_cost(re.compile(re.escape("{W}")))

def test_search_pt(simple_card):
    assert simple_card.search_pt(re.compile(r"2/2"))
    assert not simple_card.search_pt(re.compile(r"1/1"))

    # bside pt
    pt_bside = Card({
        "name": "Side A", "types": ["Sorcery"], "rarity": "Common",
        "bside": {"name": "Side B", "types": ["Creature"], "rarity": "Common", "power": "1", "toughness": "1"}
    })
    assert pt_bside.search_pt(re.compile(r"1/1"))

def test_search_loyalty(planeswalker_card):
    assert planeswalker_card.search_loyalty(re.compile(r"3"))
    assert not planeswalker_card.search_loyalty(re.compile(r"4"))

    # bside loyalty
    loyalty_bside = Card({
        "name": "Side A", "types": ["Sorcery"], "rarity": "Common",
        "bside": {"name": "Side B", "types": ["Planeswalker"], "rarity": "Common", "loyalty": 5}
    })
    assert loyalty_bside.search_loyalty(re.compile(r"5"))

def test_search_aggregate(simple_card, split_card, planeswalker_card):
    # name
    assert simple_card.search(re.compile(r"grizzly", re.IGNORECASE))
    # type
    assert simple_card.search(re.compile(r"creature", re.IGNORECASE))
    # text
    assert simple_card.search(re.compile(r"win", re.IGNORECASE))
    # cost
    assert simple_card.search(re.compile(re.escape("{1}{G}")))
    # pt
    assert simple_card.search(re.compile(r"2/2"))
    # loyalty
    assert planeswalker_card.search(re.compile(r"3"))

    # bside
    assert split_card.search(re.compile(r"ice", re.IGNORECASE))
    assert split_card.search(re.compile(r"draw", re.IGNORECASE))

    assert not simple_card.search(re.compile(r"nomatch"))
