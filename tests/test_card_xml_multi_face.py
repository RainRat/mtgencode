import sys
import os
import pytest

libdir = os.path.join(os.getcwd(), 'lib')
sys.path.append(libdir)
import cardlib

def test_xml_multi_face_both_stats():
    card_json = {
        "name": "Side A",
        "manaCost": "{1}{W}",
        "types": ["Creature"],
        "power": "&^^",
        "toughness": "&^^",
        "bside": {
            "name": "Side B",
            "manaCost": "",
            "types": ["Creature"],
            "power": "&^^^",
            "toughness": "&^^^"
        }
    }
    card = cardlib.Card(card_json)
    xml = card.to_cockatrice_xml()
    assert "<pt>2/2 // 3/3</pt>" in xml
    assert "<tablerow>2</tablerow>" in xml

def test_xml_multi_face_bside_stats_only():
    card_json = {
        "name": "Side A",
        "manaCost": "{2}{U}",
        "types": ["Artifact"],
        "bside": {
            "name": "Side B",
            "manaCost": "",
            "types": ["Creature"],
            "power": "&^^^",
            "toughness": "&^^^"
        }
    }
    card = cardlib.Card(card_json)
    xml = card.to_cockatrice_xml()
    assert "<pt>3/3</pt>" in xml
    assert "<tablerow>2</tablerow>" in xml

def test_xml_multi_face_aside_stats_only():
    card_json = {
        "name": "Side A",
        "manaCost": "{R}",
        "types": ["Creature"],
        "power": "&^",
        "toughness": "&^",
        "bside": {
            "name": "Side B",
            "manaCost": "{1}{R}",
            "types": ["Instant"]
        }
    }
    card = cardlib.Card(card_json)
    xml = card.to_cockatrice_xml()
    assert "<pt>1/1</pt>" in xml
    assert "<tablerow>2</tablerow>" in xml

def test_xml_multi_face_tablerow_priority():
    card_json = {
        "name": "Side A",
        "manaCost": "{G}",
        "types": ["Creature"],
        "power": "&^^",
        "toughness": "&^^",
        "bside": {
            "name": "Side B",
            "types": ["Land"]
        }
    }
    card = cardlib.Card(card_json)
    xml = card.to_cockatrice_xml()
    assert "<tablerow>0</tablerow>" in xml

    card_json = {
        "name": "Side A",
        "manaCost": "{1}",
        "types": ["Artifact"],
        "bside": {
            "name": "Side B",
            "manaCost": "{U}",
            "types": ["Instant"]
        }
    }
    card = cardlib.Card(card_json)
    xml = card.to_cockatrice_xml()
    assert "<tablerow>3</tablerow>" in xml

def test_xml_loyalty_multi_face():
    card_json = {
        "name": "Side A",
        "manaCost": "{2}{W}{W}",
        "types": ["Planeswalker"],
        "loyalty": "&^^^",
        "bside": {
            "name": "Side B",
            "manaCost": "",
            "types": ["Creature"],
            "power": "&^^^^",
            "toughness": "&^^^^"
        }
    }
    card = cardlib.Card(card_json)
    xml = card.to_cockatrice_xml()
    assert "<pt>3 // 4/4</pt>" in xml
    assert "<tablerow>2</tablerow>" in xml

if __name__ == "__main__":
    pytest.main([__file__])
