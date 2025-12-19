import pytest
from lib.cardlib import Card
from lib import config

@pytest.fixture
def split_card_json():
    return {
        "name": "Fire",
        "manaCost": "{1}{R}",
        "type": "Instant",
        "types": ["Instant"],
        "supertypes": [],
        "subtypes": [],
        "rarity": "Uncommon",
        "text": "Fire deals 2 damage divided as you choose among one or two target creatures and/or players.",
        "bside": {
            "name": "Ice",
            "manaCost": "{1}{U}",
            "type": "Instant",
            "types": ["Instant"],
            "supertypes": [],
            "subtypes": [],
            "rarity": "Uncommon",
            "text": "Tap target permanent.\nDraw a card."
        }
    }

def test_bside_initialization_from_json(split_card_json):
    card = Card(split_card_json)
    assert card.name == "fire"
    assert card.bside is not None
    assert card.bside.name == "ice"
    # Text is processed and uses internal newline marker
    expected_text = "tap target permanent." + config.newline + "draw a card."
    assert card.bside.text.text == expected_text
    assert card.valid
    assert card.bside.valid

def test_bside_encode_decode(split_card_json):
    original_card = Card(split_card_json)
    encoded = original_card.encode()

    # Check that encoded string contains the separator (newline)
    assert "\n" in encoded

    # Decode
    decoded_card = Card(encoded)
    assert decoded_card.name == "fire"
    assert decoded_card.bside is not None
    assert decoded_card.bside.name == "ice"

    expected_text = "tap target permanent." + config.newline + "draw a card."
    assert decoded_card.bside.text.text == expected_text

def test_bside_vectorize(split_card_json):
    card = Card(split_card_json)
    vectorized = card.vectorize()

    assert "_ASIDE_" in vectorized
    assert "_BSIDE_" in vectorized
    # Rarity is abbreviated (Uncommon -> N) and wrapped in parens
    assert "(N)" in vectorized
    assert "(instant)" in vectorized

def test_bside_to_mse(split_card_json):
    card = Card(split_card_json)
    mse = card.to_mse()

    assert "stylesheet: new-split" in mse
    assert "name: Fire" in mse
    assert "name 2: Ice" in mse
    assert "rule text:" in mse
    assert "rule text 2:" in mse

def test_bside_custom_format(split_card_json):
    # Use a custom format that excludes name (fmt_ordered_noname)
    from lib.cardlib import fmt_ordered_noname

    card = Card(split_card_json, fmt_ordered=fmt_ordered_noname)
    encoded = card.encode(fmt_ordered=fmt_ordered_noname)

    # Decode using the same format
    decoded = Card(encoded, fmt_ordered=fmt_ordered_noname)

    # fmt_ordered_noname does not include field_name, so name is not encoded/decoded
    assert decoded.name == ""
    assert decoded.bside is not None
    assert decoded.bside.name == ""
    # Text should still be preserved
    # "Fire deals" -> "@ deals" (where @ is this_marker)
    assert "@ deals" in decoded.text.text

    expected_text = "tap target permanent." + config.newline + "draw a card."
    assert decoded.bside.text.text == expected_text
