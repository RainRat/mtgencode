import pytest
import re
from lib.cardlib import Card, field_name, field_types, field_pt, field_text, field_other, field_loyalty
import lib.utils as utils

def test_card_summary_bside():
    card_json = {
        "name": "Side A",
        "types": ["Creature"],
        "rarity": "Common",
        "bside": {
            "name": "Side B",
            "types": ["Instant"]
        }
    }
    card = Card(card_json)
    summary = card.summary()
    assert "Side A" in summary
    assert "Side B" in summary
    assert " // " in summary

def test_card_format_vdump_no_name_no_type():
    # Trigger line 998 and 1049
    card_json = {
        "name": "",
        "types": []
    }
    card = Card(card_json)
    formatted = card.format(vdump=True, gatherer=True)
    assert "_NONAME_" in formatted
    assert "_NOTYPE_" in formatted

def test_card_format_bside_variants():
    # Trigger lines 1127-1135
    card_json = {
        "name": "A", "types": ["Land"],
        "bside": {"name": "B", "types": ["Land"]}
    }
    card = Card(card_json)

    # Standard
    fmt = card.format()
    assert "~~~~ (B-Side) ~~~~" in fmt

    # ANSI Color
    fmt_color = card.format(ansi_color=True)
    assert "\033[" in fmt_color

    # Markdown
    fmt_md = card.format(for_md=True)
    assert "~~~~~~~~" in fmt_md

def test_card_to_dict_metadata_and_pt():
    # Trigger lines 1175, 1191, 1193
    card_json = {
        "name": "Test",
        "types": ["Creature"],
        "pt": "1/1",
        "setCode": "EXP",
        "number": "42"
    }
    card = Card(card_json)
    # Manually set pt to something without '/' to hit line 1175
    card.pt = "7"
    d = card.to_dict()
    assert d['pt'] == "7"
    assert d['setCode'] == "EXP"
    assert d['number'] == "42"

def test_card_to_mse_bside_complex():
    # Trigger lines 1266, 1280, 1284-1287
    card_json = {
        "name": "A", "types": ["Creature"], "rarity": "rare",
        "bside": {
            "name": "B", "types": ["Creature"], "subtypes": ["Warrior"],
            "rarity": "special", "power": "2", "toughness": "2"
        }
    }
    card = Card(card_json)
    mse = card.to_mse()
    assert "name 2: B" in mse
    assert "rarity 2: special" in mse
    assert "sub type 2: Warrior" in mse
    assert "power 2: 2" in mse
    assert "toughness 2: 2" in mse

def test_card_to_markdown_row_variants():
    # Trigger lines 1346, 1380
    card_json = {
        "name": "A", "types": ["Land"], "rarity": "Common",
        "bside": {
            "name": "B", "types": ["Land"], "rarity": "Rare"
        }
    }
    card = Card(card_json)
    row = card.to_markdown_row()
    assert "common // rare" in row or "Common // Rare" in row

    # No cost
    card_no_cost = Card({"name": "C", "types": ["Land"]})
    row_no_cost = card_no_cost.to_markdown_row()
    assert "| C |" in row_no_cost

def test_card_encode_invalid_field():
    # Trigger line 806
    card = Card({"name": "Test", "types": ["Land"]})
    with pytest.raises(ValueError, match="unknown field for Card.encode"):
        card.encode(fmt_ordered=["nonexistent_field"])

def test_card_set_pt_multiple_and_invalid():
    # Trigger lines 630-632, 636-637
    # We can't easily trigger this via constructor because it uses a dict.
    # We'll call _set_pt directly.
    card = Card({"name": "Test", "types": ["Creature"]})
    card.verbose = True
    # Invalid P/T (missing /)
    card._set_pt([(-1, "7")])
    assert card.valid == False

    # Multiple P/T
    card._set_pt([(0, "1/1"), (1, "2/2")])
    assert card.valid == False

def test_card_set_text_multiple():
    # Trigger line 656-657
    card = Card({"name": "Test", "types": ["Instant"]})
    # Multiple text values
    card._set_text([(0, card.text), (1, card.text)])
    assert card.valid == False

def test_card_format_other_fields():
    # Trigger lines 1110, 1114
    card = Card({"name": "Test", "types": ["Land"]})
    card_other_fields = [(0, "extra1"), (1, "extra2")]
    setattr(card, field_other, card_other_fields)

    # HTML
    fmt_html = card.format(for_html=True, vdump=True)
    assert "<br>\n(1) extra2" in fmt_html

    # Markdown
    fmt_md = card.format(for_md=True, vdump=True)
    assert "  \n(1) extra2" in fmt_md

def test_card_fields_from_format_multiple():
    # Trigger line 365
    # Encoded card with duplicate name field
    card = Card("|1Name1|1Name2|5land|")
    assert card.valid == False

def test_card_constructor_unknown_field():
    # Trigger line 500
    with pytest.raises(ValueError, match="unknown field for Card"):
        Card("Test", fmt_ordered=["unknown_field"])

def test_card_set_loyalty_multiple():
    # Trigger line 612-615
    card = Card({"name": "Test", "types": ["Planeswalker"], "loyalty": "3"})
    card.verbose = True
    card._set_loyalty([(0, "3"), (1, "4")])
    assert card.valid == False

def test_card_to_mse_rarity_not_in_unmap():
    # Trigger line 1224
    card = Card({"name": "Test", "types": ["Land"]})
    card.rarity = "SuperRare"
    mse = card.to_mse()
    assert "rarity: superrare" in mse
