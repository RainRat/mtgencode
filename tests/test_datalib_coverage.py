
import pytest
import sys
import os

# Ensure lib is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib')))

from datalib import Datamine
from cardlib import Card

@pytest.fixture
def comprehensive_cards_data():
    return [
        {
            "name": "Card A",
            "types": ["Creature"],
            "supertypes": ["Legendary"],
            "pt": "1/1",
            "manaCost": "{R}",
            "cmc": 1,
            "colors": ["R"],
            "text": "Flying",
            "rarity": "Common"
        },
        {
            "name": "Card A", # Duplicate name
            "types": ["Instant"],
            "manaCost": "{U}",
            "cmc": 1,
            "colors": ["U"],
            "text": "Draw a card.",
            "rarity": "Uncommon"
        },
        {
            "name": "Planeswalker D",
            "types": ["Planeswalker"],
            "manaCost": "{2}{W}{W}",
            "cmc": 4,
            "colors": ["W"],
            "text": "+1: Scry 1.",
            "rarity": "Mythic",
            "loyalty": "3"
        },
        {"garbage": "data"}, # Unparsed (missing name)
        {"name": "Invalid", "types": ["Creature"], "rarity": "Common"} # Parsed but invalid (missing P/T for creature)
    ]

def test_summarize_with_color(comprehensive_cards_data, capsys):
    dm = Datamine(comprehensive_cards_data)
    dm.summarize(use_color=True)
    captured = capsys.readouterr()
    output = captured.out

    # Check for color codes (ANSI escape sequences)
    assert "\033[" in output
    assert "DATASET SUMMARY" in output
    assert "COLORS & MANA" in output
    assert "CARD TYPES" in output
    assert "STATS & RARITY" in output
    assert "CONTENT & MECHANICS" in output

    # Check specific colorized breakdown logic
    assert "common" in output.lower()
    assert "R" in output
    assert "{R}" in output
    assert "1/1" in output
    assert "3" in output

def test_outliers_comprehensive(comprehensive_cards_data, capsys):
    dm = Datamine(comprehensive_cards_data)

    # Test outliers with color, dump_invalid=True, and duplicate names
    dm.outliers(use_color=True, dump_invalid=True)
    captured = capsys.readouterr()
    output = captured.out

    assert "OUTLIER ANALYSIS" in output
    assert "\033[" in output
    assert "Most duplicated names:" in output
    assert "card a" in output.lower()
    assert "invalid cards" in output
    assert "unparsed cards" in output
    assert "by_name" in output
    assert "by_type" in output
    assert "legendary" in output.lower()

def test_outliers_no_dump_invalid(comprehensive_cards_data, capsys):
    dm = Datamine(comprehensive_cards_data)

    # Test outliers with dump_invalid=False (default) to cover "Not summarizing." lines
    dm.outliers(dump_invalid=False)
    captured = capsys.readouterr()
    output = captured.out

    assert "Not summarizing." in output

def test_outliers_empty_indices(capsys):
    # Empty datamine
    dm = Datamine([])
    dm.outliers()
    captured = capsys.readouterr()
    output = captured.out

    assert "No cards indexed by name?" in output
    assert "No cards indexed by type?" in output
    assert "No cards indexed by subtype?" in output
    assert "No cards indexed by supertype?" in output
    assert "No cards indexed by cost?" in output
    assert "No cards indexed by cmc?" in output
    assert "No cards indexed by power?" in output
    assert "No cards indexed by toughness?" in output
    assert "No cards indexed by line count?" in output
    assert "No cards indexed by char count?" in output

def test_inc_with_zero():
    from datalib import inc
    d = {}
    inc(d, 0, [1])
    assert 0 in d
    assert d[0] == [1]

def test_print_breakdown_empty():
    from datalib import _print_breakdown
    # Should just return without printing anything
    _print_breakdown("Empty", {}, 0, False)

def test_datamine_init_empty_item():
    dm = Datamine([None, {}])
    assert len(dm.allcards) == 0

def test_datamine_init_has_fields():
    card = Card({"name": "Test", "types": ["Instant"], "rarity": "Common"})
    dm = Datamine([card])
    assert len(dm.cards) == 1
    assert dm.cards[0] == card

def test_plimit_coverage():
    from datalib import plimit
    # Test precisely at the limit
    s = "a" * 1000
    assert plimit(s) == s
    # Test just above the limit
    s = "a" * 1001
    assert plimit(s) == ("a" * 1000 + "[...]")
