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
