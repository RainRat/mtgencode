import pytest
from lib import cardlib
from lib import sortlib

def test_sort_by_name():
    c1 = cardlib.Card({"name": "Zebra", "types": ["Creature"]})
    c2 = cardlib.Card({"name": "Apple", "types": ["Creature"]})
    cards = [c1, c2]
    sorted_cards = sortlib.sort_cards(cards, 'name')
    assert sorted_cards[0].name == "apple"
    assert sorted_cards[1].name == "zebra"

def test_sort_by_cmc():
    c1 = cardlib.Card({"name": "Big", "manaCost": "{6}{G}", "types": ["Creature"]})
    c2 = cardlib.Card({"name": "Small", "manaCost": "{G}", "types": ["Creature"]})
    cards = [c1, c2]
    sorted_cards = sortlib.sort_cards(cards, 'cmc')
    assert sorted_cards[0].name == "small"
    assert sorted_cards[1].name == "big"

def test_sort_by_color():
    c1 = cardlib.Card({"name": "White", "manaCost": "{W}", "types": ["Creature"]})
    c2 = cardlib.Card({"name": "Blue", "manaCost": "{U}", "types": ["Creature"]})
    c3 = cardlib.Card({"name": "Red", "manaCost": "{R}", "types": ["Creature"]})
    cards = [c3, c1, c2]
    sorted_cards = sortlib.sort_cards(cards, 'color')
    # Order should be W, U, B, R, G, multi, colorless, lands
    assert sorted_cards[0].name == "white"
    assert sorted_cards[1].name == "blue"
    assert sorted_cards[2].name == "red"
