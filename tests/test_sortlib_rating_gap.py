from lib import cardlib
from lib import sortlib

def test_sort_by_rating():
    c1 = cardlib.Card({"name": "Bears", "manaCost": "{1}{G}", "types": ["Creature"], "power": "2", "toughness": "2"})
    c2 = cardlib.Card({"name": "Weakling", "manaCost": "{1}{G}", "types": ["Creature"], "power": "1", "toughness": "1"})
    c3 = cardlib.Card({"name": "Strongman", "manaCost": "{1}{G}", "types": ["Creature"], "power": "4", "toughness": "4"})

    cards = [c1, c2, c3]

    sorted_cards = sortlib.sort_cards(cards, 'rating')
    assert sorted_cards[0].name == "weakling"
    assert sorted_cards[1].name == "bears"
    assert sorted_cards[2].name == "strongman"

    sorted_cards = sortlib.sort_cards(cards, 'power_rating')
    assert sorted_cards[0].name == "weakling"
    assert sorted_cards[1].name == "bears"
    assert sorted_cards[2].name == "strongman"

    sorted_cards = sortlib.sort_cards(cards, 'rating', reverse=True)
    assert sorted_cards[0].name == "strongman"
    assert sorted_cards[1].name == "bears"
    assert sorted_cards[2].name == "weakling"
