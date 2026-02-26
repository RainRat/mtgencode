
import pytest
import sys
import os
import io

# Ensure lib is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'lib')))

from datalib import Datamine
import utils

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
        },
        {
            "name": "Card D",
            "types": ["Planeswalker"],
            "manaCost": "{3}{W}{B}",
            "cmc": 5,
            "colors": ["W", "B"],
            "text": "Text D",
            "rarity": "Mythic Rare",
            "loyalty": "3"
        }
    ]

@pytest.fixture
def datamine_instance(sample_cards_data):
    return Datamine(sample_cards_data)

def test_rarity_indexing(datamine_instance):
    dm = datamine_instance

    assert 'by_rarity' in dm.indices
    assert len(dm.by_rarity) == 4
    # json_rarity_unmap results in these keys based on the last-entry-wins in utils.py
    assert 'common' in dm.by_rarity
    assert 'uncommon' in dm.by_rarity
    assert 'rare' in dm.by_rarity
    assert 'mythic' in dm.by_rarity

def test_average_cmc(datamine_instance):
    dm = datamine_instance

    # CMCs: 1, 1, 2, 5 -> Sum = 9. Count = 4. Avg = 2.25
    expected_avg = 2.25

    # Calculate from dm.cards
    avg_cmc = sum(c.cost.cmc for c in dm.cards) / len(dm.cards)
    assert avg_cmc == expected_avg

def test_summarize_output(datamine_instance, capsys):
    datamine_instance.summarize()
    captured = capsys.readouterr()
    output = captured.out

    assert "Average CMC: 2.25" in output
    assert "4 represented rarities" in output
    assert "Breakdown by rarity:" in output
    assert "common" in output
    assert "uncommon" in output
    assert "rare" in output
    assert "mythic" in output

def test_to_dict_avg_cmc(datamine_instance):
    result = datamine_instance.to_dict()
    assert 'avg_cmc' in result['stats']
    assert result['stats']['avg_cmc'] == 2.25

    assert 'by_rarity' in result['indices']
    assert result['indices']['by_rarity']['common'] == 1
    assert result['indices']['by_rarity']['mythic'] == 1
