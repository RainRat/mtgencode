import pytest
from lib.cardlib import Card

@pytest.fixture
def sample_card_json():
    return {
        "name": "Ornithopter",
        "manaCost": "{0}",
        "cmc": 0,
        "colors": [],
        "type": "Artifact Creature — Thopter",
        "supertypes": [],
        "types": ["Artifact", "Creature"],
        "subtypes": ["Thopter"],
        "rarity": "Uncommon",
        "text": "Flying",
        "power": "0",
        "toughness": "2"
    }

def test_card_initialization_from_json(sample_card_json):
    card = Card(sample_card_json)
    assert card.name == "ornithopter"
    assert card.cost.cmc == 0
    assert card.types == ["artifact", "creature"]
    assert card.subtypes == ["thopter"]
    assert card.pt == "&/&^^"
    assert card.text.text == "flying"
    assert card.valid

def test_planeswalker_to_mse_formatting():
    planeswalker_json = {
        "name": "Jules, the Wise",
        "manaCost": "{3}{U}{U}",
        "type": "Legendary Planeswalker — Jules",
        "supertypes": ["Legendary"],
        "types": ["Planeswalker"],
        "subtypes": ["Jules"],
        "rarity": "Mythic",
        "text": "You may cast spells from the top of your library.\n+1: Scry 1.\n-8: You get an emblem with \"You have no maximum hand size.\"",
        "loyalty": 4
    }
    card = Card(planeswalker_json)
    mse_output = card.to_mse()
    expected_output = """card:
	name: Jules, the Wise
	rarity: mythic
	casting cost: 3UU
	super type: Legendary Planeswalker
	sub type: Jules
	stylesheet: m15-planeswalker
	loyalty cost 1: +1
	loyalty cost 2: -8
	loyalty: 4
	rule text:
		You may cast spells from the top of your library.
		Scry 1.
		You get an emblem with "you have no maximum hand size."
	has styling: false
	time created:2015-07-20 22:53:07
	time modified:2015-07-20 22:53:08
	extra data:
	image:
	card code text:
	copyright:
	image 2:
	copyright 2:
	notes:"""

    # The timestamps are dynamically generated, so we'll ignore them in the comparison
    assert mse_output.strip().split('has styling')[0] == expected_output.strip().split('has styling')[0]

def test_card_initialization_from_encoded_text():
    encoded_text = "|5artifact creature|4|6thopter|8&/&^^|9flying|3{}|0N|1ornithopter|"
    card = Card(encoded_text, fmt_ordered=[
    "types",
    "supertypes",
    "subtypes",
    "loyalty",
    "pt",
    "text",
    "cost",
    "rarity",
    "name",
])
    assert card.name == "ornithopter"
    assert card.cost.cmc == 0
    assert card.types == ["artifact", "creature"]
    assert card.subtypes == ["thopter"]
    assert card.pt == "&/&^^"
    assert card.text.text == "flying"
    assert card.valid
