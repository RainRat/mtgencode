import pytest
import re
from lib.cardlib import Card, fields_from_json
from lib import utils

def test_card_type_properties():
    land = Card({"name": "Plains", "types": ["Land"], "rarity": "Common"})
    assert land.is_land
    assert not land.is_enchantment
    assert not land.is_instant
    assert not land.is_sorcery

    enchantment = Card({"name": "Anthem", "types": ["Enchantment"], "rarity": "Rare"})
    assert enchantment.is_enchantment
    assert not land.is_enchantment

    instant = Card({"name": "Shock", "types": ["Instant"], "rarity": "Common"})
    assert instant.is_instant
    assert not instant.is_sorcery

    sorcery = Card({"name": "Divination", "types": ["Sorcery"], "rarity": "Common"})
    assert sorcery.is_sorcery
    assert not sorcery.is_instant

def test_to_cockatrice_xml_planeswalker_loyalty():
    pw = Card({
        "name": "Jace",
        "manaCost": "{1}{U}{U}",
        "types": ["Planeswalker"],
        "loyalty": 3,
        "rarity": "Rare"
    })
    xml = pw.to_cockatrice_xml()
    assert "<pt>3</pt>" in xml
    assert "<tablerow>1</tablerow>" in xml

def test_to_cockatrice_xml_split_card_merging():
    split = Card({
        "name": "Fire",
        "manaCost": "{1}{R}",
        "types": ["Instant"],
        "rarity": "Uncommon",
        "text": "Fire deals 2.",
        "bside": {
            "name": "Ice",
            "manaCost": "{1}{U}",
            "types": ["Instant"],
            "rarity": "Uncommon",
            "text": "Tap. Draw."
        }
    })
    xml = split.to_cockatrice_xml()
    assert "<name>Fire // Ice</name>" in xml
    assert "<manacost>1R</manacost>" in xml
    assert "<type>Instant // Instant</type>" in xml
    assert "<color>RU</color>" in xml
    assert "<tablerow>3</tablerow>" in xml

def test_to_cockatrice_xml_land_tablerow():
    land = Card({"name": "Forest", "types": ["Land"], "rarity": "Basic Land"})
    xml = land.to_cockatrice_xml()
    assert "<tablerow>0</tablerow>" in xml

def test_to_cockatrice_xml_sorcery_tablerow():
    sorcery = Card({"name": "Fear", "types": ["Sorcery"], "rarity": "Common"})
    xml = sorcery.to_cockatrice_xml()
    assert "<tablerow>3</tablerow>" in xml

def test_mana_translate_unrecognized_token_fallback():
    res = utils.mana_translate("{W/U/B}")
    assert res == "{{W/U/B}}"

def test_fields_from_json_supertypes_parsing():
    src = {
        "name": "Thrun",
        "supertypes": ["Legendary"],
        "types": ["Creature"],
        "rarity": "Rare"
    }
    parsed, valid, fields = fields_from_json(src)
    assert "supertypes" in fields
    assert fields["supertypes"] == [(-1, ["legendary"])]

def test_card_display_data_ansi_color_formatting():
    card = Card({
        "name": "Shock",
        "manaCost": "{R}",
        "types": ["Instant"],
        "rarity": "Common"
    })
    name, cost, cmc, typeline, stats, text, rarity, mechanics = card._get_single_face_display_data(ansi_color=True)
    assert "\033[" in name
    assert "\033[" in cmc
    assert "\033[" in typeline
    assert "\033[" in rarity

def test_card_format_html_hover_image():
    card = Card({
        "name": "Shock",
        "manaCost": "{R}",
        "types": ["Instant"],
        "rarity": "Common",
        "setCode": "TST",
        "number": "1"
    })
    html = card.format(for_html=True)
    assert '<div class="hover_img">' in html

def test_card_format_markdown_scryfall_link():
    card = Card({
        "name": "Shock",
        "manaCost": "{R}",
        "types": ["Instant"],
        "rarity": "Common",
        "setCode": "TST",
        "number": "1"
    })
    md = card.format(for_md=True)
    assert "[**Shock**](https://scryfall.com/card/tst/1)" in md

def test_card_to_dict_preserves_box_and_pack_id():
    card = Card({
        "name": "Shock",
        "types": ["Instant"],
        "rarity": "Common"
    })
    card.box_id = 1
    card.pack_id = 1
    d = card.to_dict()
    assert d['box_id'] == 1
    assert d['pack_id'] == 1
