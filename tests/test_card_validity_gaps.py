import pytest
from lib.cardlib import Card

def test_missing_types():
    card = Card({"name": "No Type Card"})
    assert card.valid is False

def test_battle_validity():
    card_no_loyalty = Card({"name": "Battle Card", "types": ["Battle"], "rarity": "rare"})
    assert card_no_loyalty.valid is False

    card_with_loyalty = Card({"name": "Battle Card", "types": ["Battle"], "loyalty": "5", "rarity": "rare"})
    assert card_with_loyalty.valid is True

def test_vehicle_is_creature():
    card_no_pt = Card({"name": "Skysovereign", "types": ["Artifact"], "subtypes": ["Vehicle"], "rarity": "rare"})
    assert card_no_pt.valid is False

    card_with_pt = Card({"name": "Skysovereign", "types": ["Artifact"], "subtypes": ["Vehicle"], "pt": "6/5", "rarity": "rare"})
    assert card_with_pt.valid is True

def test_station_pt_exception():
    card_pt_no_station = Card({"name": "Regular Artifact", "types": ["Artifact"], "pt": "1/1", "rarity": "common"})
    assert card_pt_no_station.valid is False

    card_pt_station = Card({"name": "Salvaging", "types": ["Artifact"], "text": "This station is cool", "pt": "1/1", "rarity": "rare"})
    assert card_pt_station.valid is True

    card_no_pt_station = Card({"name": "Salvaging", "types": ["Artifact"], "text": "This station is cool", "rarity": "rare"})
    assert card_no_pt_station.valid is True

def test_non_creature_with_pt():
    card = Card({"name": "Enchantment with PT", "types": ["Enchantment"], "pt": "1/1", "rarity": "rare"})
    assert card.valid is False
