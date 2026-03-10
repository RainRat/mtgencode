import pytest
from lib import cardlib
from lib import sortlib
from lib import utils

def test_sort_rarity():
    # Card objects store rarity markers ('Y', 'A', 'N', 'O', etc.) internally
    c1 = cardlib.Card({"name": "Common", "rarity": "Common"}) # 'O'
    c2 = cardlib.Card({"name": "Rare", "rarity": "Rare"})     # 'A'
    c3 = cardlib.Card({"name": "Mythic", "rarity": "Mythic"}) # 'Y'
    cards = [c1, c2, c3]
    sorted_cards = sortlib.sort_cards(cards, 'rarity')
    assert sorted_cards[0].name == "mythic"
    assert sorted_cards[1].name == "rare"
    assert sorted_cards[2].name == "common"

def test_sort_power():
    c1 = cardlib.Card({"name": "Small", "power": "1", "toughness": "1", "types": ["Creature"]})
    c2 = cardlib.Card({"name": "Big", "power": "5", "toughness": "5", "types": ["Creature"]})
    c3 = cardlib.Card({"name": "None", "types": ["Instant"]})
    cards = [c1, c2, c3]
    sorted_cards = sortlib.sort_cards(cards, 'power')
    assert sorted_cards[0].name == "big"
    assert sorted_cards[1].name == "small"
    assert sorted_cards[2].name == "none"

def test_sort_loyalty():
    c1 = cardlib.Card({"name": "Low", "types": ["Planeswalker"], "loyalty": "3"})
    c2 = cardlib.Card({"name": "High", "types": ["Planeswalker"], "loyalty": "5"})
    c3 = cardlib.Card({"name": "None", "types": ["Creature"], "pt": "1/1"})
    cards = [c1, c2, c3]
    sorted_cards = sortlib.sort_cards(cards, 'loyalty')
    assert sorted_cards[0].name == "high"
    assert sorted_cards[1].name == "low"
    assert sorted_cards[2].name == "none"

def test_sort_set():
    c1 = cardlib.Card({"name": "A", "setCode": "ABC", "number": "1"})
    c2 = cardlib.Card({"name": "B", "setCode": "ABC", "number": "10"})
    c3 = cardlib.Card({"name": "C", "setCode": "XYZ", "number": "5"})
    cards = [c3, c2, c1]
    sorted_cards = sortlib.sort_cards(cards, 'set')
    assert sorted_cards[0].name == "a"
    assert sorted_cards[1].name == "b"
    assert sorted_cards[2].name == "c"
