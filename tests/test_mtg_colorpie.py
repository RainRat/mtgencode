import pytest
import os
import sys
import json
from unittest.mock import patch, MagicMock
from io import StringIO

# Add lib and scripts directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../lib'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))

import mtg_colorpie
import cardlib

@pytest.fixture
def sample_cards():
    card1 = MagicMock(spec=cardlib.Card)
    card1.name = "White Weenie"
    card1.color_identity = "W"
    card1.mechanics = {"Flying", "Vigilance"}
    card1.valid = True
    card1.parsed = True

    card2 = MagicMock(spec=cardlib.Card)
    card2.name = "Blue Flyer"
    card2.color_identity = "U"
    card2.mechanics = {"Flying", "Ward"}
    card2.valid = True
    card2.parsed = True

    card3 = MagicMock(spec=cardlib.Card)
    card3.name = "Gold Spell"
    card3.color_identity = "WU"
    card3.mechanics = {"Flying"}
    card3.valid = True
    card3.parsed = True

    return [card1, card2, card3]

def test_get_color_group():
    card = MagicMock()
    card.color_identity = "W"
    assert mtg_colorpie.get_color_group(card) == "W"

    card.color_identity = "WUBRG"
    assert mtg_colorpie.get_color_group(card) == "M"

    card.color_identity = ""
    assert mtg_colorpie.get_color_group(card) == "A"

def test_mtg_colorpie_main_basic(sample_cards):
    with patch('jdecode.mtg_open_file', return_value=sample_cards), \
         patch('sys.stdout', new=StringIO()) as fake_out, \
         patch('sys.argv', ['mtg_colorpie.py', 'dummy.json', '--no-color']):
        mtg_colorpie.main()
        output = fake_out.getvalue()
        assert "MECHANICAL COLOR PIE" in output
        assert "Flying" in output
        assert "Vigilance" in output
        assert "Ward" in output

def test_mtg_colorpie_json(sample_cards):
    with patch('jdecode.mtg_open_file', return_value=sample_cards), \
         patch('sys.stdout', new=StringIO()) as fake_out, \
         patch('sys.argv', ['mtg_colorpie.py', 'dummy.json', '--json']):
        mtg_colorpie.main()
        output = fake_out.getvalue()
        data = json.loads(output)
        assert "primary" in data
        assert data["primary"]["total"] == 3
        assert data["primary"]["groups"]["W"] == 1
        assert data["primary"]["groups"]["U"] == 1
        assert data["primary"]["groups"]["M"] == 1
        assert data["primary"]["mechanics"]["W"]["Flying"] == 1
        assert data["primary"]["mechanics"]["U"]["Ward"] == 1

def test_mtg_colorpie_compare(sample_cards):
    with patch('jdecode.mtg_open_file', side_effect=[sample_cards, sample_cards]), \
         patch('sys.stdout', new=StringIO()) as fake_out, \
         patch('sys.argv', ['mtg_colorpie.py', 'dummy1.json', '--compare', 'dummy2.json', '--no-color']):
        mtg_colorpie.main()
        output = fake_out.getvalue()
        assert "MECHANICAL COLOR PIE (COMPARISON)" in output
        assert "Flying" in output
