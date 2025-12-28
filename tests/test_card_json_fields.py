import pytest
from lib.cardlib import fields_from_json, field_loyalty, field_pt, field_subtypes, field_rarity, field_types, field_name
from lib import utils

def test_fields_from_json_basic_name():
    src_json = {"name": "Test Card"}
    parsed, valid, fields = fields_from_json(src_json)
    assert not parsed
    assert fields[field_name][0][1] == "test card"

def test_fields_from_json_types_required():
    src_json = {"name": "Test Card", "types": ["Creature"]}
    parsed, valid, fields = fields_from_json(src_json)
    assert not parsed
    assert fields[field_types][0][1] == ["creature"]

def test_fields_from_json_rarity_fallback():
    src_json = {"name": "Test", "types": ["Creature"], "rarity": "Common"}
    parsed, valid, fields = fields_from_json(src_json)
    assert parsed
    assert fields[field_rarity][0][1] == utils.rarity_common_marker

    src_json = {"name": "Test", "types": ["Creature"], "rarity": "Ultra Rare"}
    parsed, valid, fields = fields_from_json(src_json)
    assert not parsed
    assert fields[field_rarity][0][1] == "Ultra Rare"

def test_fields_from_json_loyalty_vs_defense():
    src_json = {"name": "PW", "types": ["Planeswalker"], "rarity": "Mythic", "loyalty": "4"}
    parsed, valid, fields = fields_from_json(src_json)
    assert parsed
    assert fields[field_loyalty][0][1] == utils.to_unary("4")

    src_json = {"name": "Battle", "types": ["Battle"], "rarity": "Rare", "defense": "5"}
    parsed, valid, fields = fields_from_json(src_json)
    assert parsed
    assert fields[field_loyalty][0][1] == utils.to_unary("5")

    src_json = {"name": "Weird", "types": ["Battle"], "rarity": "Rare", "loyalty": "3", "defense": "5"}
    parsed, valid, fields = fields_from_json(src_json)
    assert parsed
    assert fields[field_loyalty][0][1] == utils.to_unary("3")

def test_fields_from_json_pt_logic():
    base_json = {"name": "Critter", "types": ["Creature"], "rarity": "Common"}

    src = base_json.copy()
    src["pt"] = "1/1"
    parsed, valid, fields = fields_from_json(src)
    assert parsed
    assert fields[field_pt][0][1] == "1/1"

    src = base_json.copy()
    src["power"] = "2"
    parsed, valid, fields = fields_from_json(src)
    assert not parsed
    expected_p = utils.to_ascii(utils.to_unary("2")) + "/"
    assert fields[field_pt][0][1] == expected_p

    src = base_json.copy()
    src["toughness"] = "3"
    parsed, valid, fields = fields_from_json(src)
    assert not parsed
    expected_t = "/" + utils.to_ascii(utils.to_unary("3"))
    assert fields[field_pt][0][1] == expected_t

    src = base_json.copy()
    src["power"] = "4"
    src["toughness"] = "5"
    parsed, valid, fields = fields_from_json(src)
    assert parsed
    p = utils.to_ascii(utils.to_unary("4"))
    t = utils.to_ascii(utils.to_unary("5"))
    assert fields[field_pt][0][1] == p + "/" + t

def test_fields_from_json_subtypes_sanitization():
    src_json = {
        "name": "Land",
        "types": ["Land"],
        "rarity": "Common",
        "subtypes": ['Urza"s', 'Power-Plant']
    }
    parsed, valid, fields = fields_from_json(src_json)
    assert parsed
    subtypes = fields[field_subtypes][0][1]

    expected_urza = "urza's"
    expected_pp = "power" + utils.dash_marker + "plant"

    assert expected_urza in subtypes
    assert expected_pp in subtypes

def test_fields_from_json_text_station():
    src_json = {
        "name": "Test Station",
        "types": ["Artifact"],
        "rarity": "Common",
        "text": "{T}: Add {1}."
    }
    parsed, valid, fields = fields_from_json(src_json)
    assert parsed
    text_obj = fields["text"][0][1]

    formatted = str(text_obj)

    assert len(text_obj.costs) > 0
    assert f"{utils.tap_marker}: add {{1}}." in formatted
