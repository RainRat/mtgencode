import sys
import os
import pytest

libdir = os.path.join(os.getcwd(), 'lib')
sys.path.append(libdir)
import cardlib


def test_xml_escaping_special_characters():
    card_json = {
        "name": "Tom & Jerry <Special>",
        "manaCost": "{1}{R}",
        "types": ["Creature"],
        "subtypes": ["Cat"],
        "power": "&^^",
        "toughness": "&^^",
        "text": "When <this> enters, draw <a card>.",
        "setCode": "TST"
    }
    card = cardlib.Card(card_json)
    xml = card.to_cockatrice_xml()

    assert "<name>Tom &amp; Jerry &lt;special&gt;</name>" in xml
    assert "<text>When &lt;this&gt; enters, draw &lt;a card&gt;.</text>" in xml


def test_xml_empty_mana_cost_handling():
    card_json = {
        "name": "Ornithopter",
        "manaCost": "",
        "types": ["Artifact", "Creature"],
        "subtypes": ["Thopter"],
        "power": "&",
        "toughness": "&^^",
        "text": "Flying"
    }
    card = cardlib.Card(card_json)
    xml = card.to_cockatrice_xml()

    assert "<name>Ornithopter</name>" in xml
    assert "<manacost>0</manacost>" in xml
    assert "<color></color>" in xml


def test_xml_single_face_planeswalker_loyalty():
    card_json = {
        "name": "Jace, the Mind Sculptor",
        "manaCost": "{2}{U}{U}",
        "types": ["Planeswalker"],
        "subtypes": ["Jace"],
        "loyalty": "&^^^^",
        "text": "+2: Look at the top card of target player's library."
    }
    card = cardlib.Card(card_json)
    xml = card.to_cockatrice_xml()

    assert "<name>Jace, the Mind Sculptor</name>" in xml
    assert "<pt>4</pt>" in xml
    assert "<tablerow>1</tablerow>" in xml


def test_xml_multi_face_combined_fields():
    card_json = {
        "name": "Fire",
        "manaCost": "{1}{R}",
        "types": ["Instant"],
        "text": "Fire deals 2 damage divided as you choose among one or two targets.",
        "bside": {
            "name": "Ice",
            "manaCost": "{1}{U}",
            "types": ["Instant"],
            "text": "Tap target permanent. Draw a card."
        }
    }
    card = cardlib.Card(card_json)
    xml = card.to_cockatrice_xml()

    assert "<name>Fire // Ice</name>" in xml
    assert "<color>RU</color>" in xml
    assert "<manacost>1R</manacost>" in xml
    assert "<type>Instant // Instant</type>" in xml
    assert "<tablerow>3</tablerow>" in xml
    assert "<text>Fire deals 2 damage divided as you choose among one or two targets.\n\n---\n\nTap target permanent. Draw a card.</text>" in xml


if __name__ == "__main__":
    pytest.main([__file__])
