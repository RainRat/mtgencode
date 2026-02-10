
import pytest
import sys
import os
import io

# Ensure lib is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib')))

from datalib import Datamine, padrows, index_size, inc, plimit
from cardlib import Card

# Sample Data Fixture
@pytest.fixture
def sample_cards_data():
    return [
        {
            "name": "Card A",
            "types": ["Creature"],
            "pt": "1/1",
            "manaCost": "{R}",
            "cmc": 1,
            "colors": ["R"],
            "text": "Text A",
            "rarity": "Common"
        },
        {
            "name": "Card B",
            "types": ["Instant"],
            "manaCost": "{U}",
            "cmc": 1,
            "colors": ["U"],
            "text": "Text B",
            "rarity": "Uncommon"
        },
        {
            "name": "Card C",
            "types": ["Creature", "Artifact"],
            "subtypes": ["Construct"],
            "pt": "2/2",
            "manaCost": "{2}",
            "cmc": 2,
            "colors": [],
            "text": "Text C",
            "rarity": "Rare"
        }
    ]

@pytest.fixture
def datamine_instance(sample_cards_data):
    return Datamine(sample_cards_data)

# Test Helper Functions
def test_padrows():
    data = [['A', 'BB'], ['CCC', 'D']]
    padded = padrows(data)
    # lens: col1=3, col2=2
    # Row 1: 'A' -> 'A  ' (3 chars), 'BB' -> 'BB ' (2 chars + 1 space padding in loop?)
    # Let's verify exact output
    # padrows implementation:
    # lens gets max length for each column.
    # padded: val + ' ' * (len - len(s)) + ' '
    # col 1 max len 3. 'A' -> 'A' + '  ' + ' ' = 'A   '
    # col 2 max len 2. 'BB' -> 'BB' + '' + ' ' = 'BB '
    # Row 1 expected: 'A   BB '

    assert len(padded) == 2
    assert padded[0].strip() == 'A   BB'
    assert padded[1].strip() == 'CCC D'

def test_index_size():
    d = {'a': [1, 2], 'b': [3]}
    assert index_size(d) == 3
    assert index_size({}) == 0

def test_inc():
    d = {}
    inc(d, 'key', 1)
    assert d['key'] == 1
    inc(d, 'key', 2)
    assert d['key'] == 3

    inc(d, '', 5) # Empty key should be ignored
    assert '' not in d

def test_plimit():
    short_str = "short"
    assert plimit(short_str) == short_str

    long_str = "a" * 1005
    limited = plimit(long_str)
    assert len(limited) == 1005 # 1000 + 5 chars for [...]
    assert limited.endswith("[...]")

# Test Datamine Class
def test_datamine_init(datamine_instance):
    assert len(datamine_instance.cards) == 3
    assert len(datamine_instance.invalid_cards) == 0
    assert len(datamine_instance.unparsed_cards) == 0

def test_datamine_indices(datamine_instance):
    dm = datamine_instance

    # Check by_name
    assert 'card a' in dm.by_name
    assert len(dm.by_name['card a']) == 1

    # Check by_type
    assert 'creature' in dm.by_type
    assert 'instant' in dm.by_type
    # 'creature artifact' should be a key for Card C (sorted/joined? check implementation)
    # cardlib.py uses ' '.join(card.types) so order matters from input or cardlib processing
    # Card C types: ["Creature", "Artifact"] -> "creature artifact" (lowercased)
    assert 'creature artifact' in dm.by_type

    # Check by_color
    assert 'R' in dm.by_color
    assert 'U' in dm.by_color
    assert 'A' in dm.by_color # Colorless Card C

    # Check by_cmc
    assert 1 in dm.by_cmc
    assert 2 in dm.by_cmc

    # Check by_pt
    # Card A: 1/1 -> unary '&/&'
    # Card C: 2/2 -> unary '&^/&^' (check utils.to_unary)
    # '1' -> '&^' per utils.py test
    keys = list(dm.by_pt.keys())
    assert len(keys) == 2 # 1/1 and 2/2

def test_datamine_summarize(datamine_instance, capsys):
    datamine_instance.summarize()
    captured = capsys.readouterr()
    output = captured.out

    assert "3 valid cards" in output
    assert "3 unique card names" in output
    assert "Breakdown by color:" in output
    assert "Breakdown by CMC:" in output
    assert "Loyalty values:" in output

def test_datamine_outliers(datamine_instance, capsys):
    datamine_instance.outliers()
    captured = capsys.readouterr()
    output = captured.out

    assert "Overview of indices:" in output
    assert "Longest Cardname:" in output
    assert "Shortest Cardname:" in output

def test_datamine_with_invalid_card():
    # Construct a card that might be invalid (missing name or types)
    # Cardlib validation: needs name and types.
    # Must not be empty dict, or Datamine skips it entirely.
    bad_card = {"garbage": "data"}
    # fields_from_json will fail to parse name, so parsed=False.

    dm = Datamine([bad_card])
    assert len(dm.cards) == 0
    assert len(dm.unparsed_cards) == 1

    # Test summarize with unparsed
    # Capture output to ensure no crash
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        dm.summarize()
    finally:
        sys.stdout = old_stdout

def test_datamine_to_dict(datamine_instance):
    result = datamine_instance.to_dict()

    # Check structure
    assert 'counts' in result
    assert 'indices' in result
    assert 'stats' in result

    # Check counts
    assert result['counts']['valid'] == 3
    assert result['counts']['invalid'] == 0
    assert result['counts']['parsed'] == 3
    assert result['counts']['unparsed'] == 0

    # Check indices
    assert 'by_name' in result['indices']
    assert result['indices']['by_name']['card a'] == 1
    assert 'by_color' in result['indices']
    assert result['indices']['by_color']['R'] == 1
    assert result['indices']['by_color']['U'] == 1
    assert result['indices']['by_color']['A'] == 1

    # Check stats
    # Text lengths in sample data: "Text A" (6), "Text B" (6), "Text C" (6)
    # Note: text.encode() might add newlines or markers.
    # Manatext("Text A").encode() -> "Text A"
    assert result['stats']['textlen_min'] == 6
    assert result['stats']['textlen_max'] == 6
    assert result['stats']['textlines_min'] == 1
    assert result['stats']['textlines_max'] == 1

def test_datamine_with_parsed_but_invalid_card():
    # Card that parses (has name/types/etc in roughly correct format)
    # but fails validation (e.g. creature without P/T)
    invalid_card = {
        "name": "Ghost",
        "types": ["Creature"],
        "rarity": "Common"
        # Missing P/T, so valid should be False
    }

    dm = Datamine([invalid_card])
    assert len(dm.cards) == 0
    # If parsed=True but valid=False -> invalid_cards
    assert len(dm.invalid_cards) == 1

    # Check summary
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        dm.summarize()
    finally:
        sys.stdout = old_stdout
