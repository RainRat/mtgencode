
import sys
import os

# Ensure lib is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib')))

from cardlib import Card, fields_from_json
import utils

def test_fields_from_json_internal_rarity_markers():
    # 'O' is the marker for Common
    src_json = {
        "name": "Test Card",
        "types": ["Instant"],
        "rarity": "O"
    }
    parsed, valid, fields = fields_from_json(src_json)
    assert parsed
    assert fields['rarity'] == [(-1, 'O')]

def test_color_identity_with_text_symbols():
    src_json = {
        "name": "Green Producer",
        "manaCost": "{1}",
        "types": ["Artifact"],
        "text": "{T}: Add {G}.",
        "rarity": "Common"
    }
    card = Card(src_json)
    assert 'G' in card.color_identity
    assert len(card.color_identity) == 1

def test_display_data_ansi_mechanics_colorization():
    src_json = {
        "name": "Fast Flyer",
        "manaCost": "{1}{U}",
        "types": ["Creature"],
        "text": "Flying, Haste",
        "rarity": "Common",
        "power": "1",
        "toughness": "1"
    }
    card = Card(src_json)
    assert 'Flying' in card.mechanics
    assert 'Haste' in card.mechanics

    data = card._get_single_face_display_data(ansi_color=True)
    mechanics_idx = 7
    mechanics_str = data[mechanics_idx]

    assert utils.Ansi.CYAN in mechanics_str
    assert "Flying" in mechanics_str
    assert "Haste" in mechanics_str
    assert utils.Ansi.RESET in mechanics_str


def test_activate_printing_with_invalid_or_missing_set_code():
    card_data = {
        "name": "Test Card",
        "types": ["Sorcery"],
        "rarity": "Common"
    }
    card = Card(card_data)
    assert not card.activate_printing(None)
    assert not card.activate_printing("")


def test_activate_printing_with_set_code_not_in_printings():
    card_data = {
        "name": "Test Card",
        "types": ["Sorcery"],
        "rarity": "Common",
        "setCode": "XYZ"
    }
    card = Card(card_data)
    assert not card.activate_printing("NOTFOUND")


def test_activate_printing_with_valid_printing_unmapped_rarity():
    card_data = {
        "name": "Test Card",
        "types": ["Sorcery"],
        "rarity": "Common",
        "setCode": "XYZ",
        "number": "1"
    }
    card = Card(card_data)
    card.add_printing("ABC", "CustomRarity", "123")
    assert card.activate_printing("ABC")
    assert card.set_code == "ABC"
    assert card.rarity == "CustomRarity"
    assert card.number == "123"


def test_activate_printing_with_valid_printing_mapped_rarity():
    card_data = {
        "name": "Test Card",
        "types": ["Sorcery"],
        "rarity": "Common",
        "setCode": "XYZ",
        "number": "1"
    }
    card = Card(card_data)
    card.add_printing("M10", "Rare", "42")
    assert card.activate_printing("M10")
    assert card.set_code == "M10"
    assert card.rarity == "A"
    assert card.number == "42"


def test_produced_colors_any_combination_and_bside():
    face1 = {
        "name": "Side A",
        "types": ["Land"],
        "text": "{T}: Add one mana of any color."
    }
    face2 = {
        "name": "Side B",
        "types": ["Land"],
        "text": "{T}: Add {G} or {W}."
    }
    face1['bside'] = face2
    card = Card(face1)
    assert card.produced_colors == {"Any"}


def test_produced_colors_symbols_and_land_types():
    card_data = {
        "name": "Multi Land",
        "types": ["Land", "Plains", "Island"],
        "text": "{T}: Add {B} or {R}."
    }
    card = Card(card_data)
    colors = card.produced_colors
    assert colors == {"W", "U", "B", "R"}


def test_produced_colors_color_names_spelled_out():
    card_data = {
        "name": "Spell Land",
        "types": ["Land"],
        "text": "Add one green mana or add three white mana."
    }
    card = Card(card_data)
    colors = card.produced_colors
    assert colors == {"G", "W"}


def test_fields_from_json_partial_power_or_toughness():
    src_power = {
        "name": "Power Only",
        "types": ["Creature"],
        "rarity": "Common",
        "power": "3"
    }
    parsed, valid, fields = fields_from_json(src_power)
    assert not parsed
    assert fields['pt'] == [(-1, '&^^^/')]

    src_toughness = {
        "name": "Toughness Only",
        "types": ["Creature"],
        "rarity": "Common",
        "toughness": "4"
    }
    parsed2, valid2, fields2 = fields_from_json(src_toughness)
    assert not parsed2
    assert fields2['pt'] == [(-1, '/&^^^^')]


def test_card_set_loyalty_and_pt_verbose_warnings(capsys):
    card = Card({
        "name": "Verbose Test",
        "types": ["Creature"],
        "rarity": "Common",
        "pt": "2/2"
    }, verbose=True)

    card._set_loyalty([(0, "^&"), (1, "^&&")])
    captured = capsys.readouterr()
    assert "Multiple loyalty values for card 'verbose test': ^&&" in captured.err
    assert not card.valid

    card.valid = True
    card._set_pt([(0, "invalid_pt_string")])
    captured = capsys.readouterr()
    assert "Invalid P/T value for card 'verbose test': invalid_pt_string" in captured.err
    assert not card.valid

    card.valid = True
    card._set_pt([(0, "^&/^&"), (1, "^&&/^&&")])
    captured = capsys.readouterr()
    assert "Multiple P/T values for card 'verbose test': ^&&/^&&" in captured.err
    assert not card.valid

    card.valid = True
    from manalib import Manatext
    card._set_text([(0, Manatext("Text 1")), (1, Manatext("Text 2"))])
    assert not card.valid


def test_card_to_markdown_row_escaping():
    card = Card({
        "name": "Pipe | Card",
        "types": ["Instant | Sorcery"],
        "text": "Choose one |\nDraw a card.",
        "rarity": "Common"
    })
    row = card.to_markdown_row()
    assert r"Pipe \| Card" in row
    assert r"Instant \| Sorcery" in row
    assert r"Choose one \|<br>Draw a card." in row
    assert "\n" not in row


def test_card_get_ansi_color_colorless_land_vs_nonland():
    nonland = Card({
        "name": "Colorless Artifact",
        "types": ["Artifact"],
        "rarity": "Common"
    })
    assert nonland._get_ansi_color() == utils.Ansi.get_color_color('A')

    land = Card({
        "name": "Colorless Land",
        "types": ["Land"],
        "rarity": "Common"
    })
    assert land._get_ansi_color() == utils.Ansi.BOLD
