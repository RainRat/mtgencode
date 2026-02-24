import pytest
import os
import sys
import tempfile

# Add lib to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import jdecode
import cardlib
import utils

@pytest.fixture
def sample_json_data():
    return {
        "data": {
            "SET1": {
                "name": "Set 1",
                "code": "SET1",
                "type": "expansion",
                "cards": [
                    {"name": "Grizzly Bears", "rarity": "Common", "types": ["Creature"], "power": "2", "toughness": "2"},
                    {"name": "Black Lotus", "rarity": "Rare", "types": ["Artifact"]},
                    {"name": "Giant Growth", "rarity": "Common", "types": ["Instant"]}
                ]
            }
        }
    }

def test_parse_decklist(tmp_path):
    decklist_content = """
    4 Grizzly Bears
    1 Black Lotus (LEA) 232
    // A comment
    2 Giant Growth
    """
    deck_file = tmp_path / "deck.txt"
    deck_file.write_text(decklist_content)

    name_counts = jdecode.parse_decklist(str(deck_file))

    assert name_counts["grizzly bears"] == 4
    assert name_counts["black lotus"] == 1
    assert name_counts["giant growth"] == 2
    assert len(name_counts) == 3

def test_decklist_filtering(sample_json_data, tmp_path):
    # Create a decklist with only some cards
    decklist_content = "1 Grizzly Bears\n2 Giant Growth"
    deck_file = tmp_path / "deck.txt"
    deck_file.write_text(decklist_content)

    # Mock mtg_open_json to return our sample data
    import json
    json_file = tmp_path / "data.json"
    json_file.write_text(json.dumps(sample_json_data))

    # Load with decklist filter
    cards = jdecode.mtg_open_file(str(json_file), decklist_file=str(deck_file))

    # Grizzly Bears (1) + Giant Growth (2) = 3 cards
    assert len(cards) == 3
    names = [c.name.lower() for c in cards]
    assert names.count("grizzly bears") == 1
    assert names.count("giant growth") == 2
    assert "black lotus" not in names

def test_decklist_non_existent_cards(sample_json_data, tmp_path):
    # Card not in database
    decklist_content = "4 Spectral Bears"
    deck_file = tmp_path / "deck.txt"
    deck_file.write_text(decklist_content)

    import json
    json_file = tmp_path / "data.json"
    json_file.write_text(json.dumps(sample_json_data))

    # Load with decklist filter
    cards = jdecode.mtg_open_file(str(json_file), decklist_file=str(deck_file))

    assert len(cards) == 0

def test_decklist_with_encoded_text(tmp_path):
    # Create encoded text cards using 'named' encoding for simplicity in test
    # fmt_ordered_named = [field_name, field_types, field_supertypes, field_subtypes, field_loyalty, field_pt, field_text, field_cost, field_rarity]
    encoded_cards = (
        "|Grizzly Bears|creature||||2/2||{1}{G}|common|" + utils.cardsep +
        "|Black Lotus|artifact||||||{0}|rare|"
    )
    text_file = tmp_path / "cards.txt"
    text_file.write_text(encoded_cards)

    # Create decklist filter (only Grizzly Bears, but 4 of them)
    decklist_content = "4 Grizzly Bears"
    deck_file = tmp_path / "deck.txt"
    deck_file.write_text(decklist_content)

    # Load with decklist filter
    # We specify encoding='named' to match our test data
    cards = jdecode.mtg_open_file(str(text_file), decklist_file=str(deck_file), fmt_ordered=cardlib.fmt_ordered_named)

    assert len(cards) == 4
    for card in cards:
        assert card.name.lower() == "grizzly bears"
