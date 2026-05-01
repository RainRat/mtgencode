import io
import sys
from unittest.mock import patch, MagicMock
import pytest
from lib import utils, cardlib, datalib, transforms

def test_print_header_coverage():
    with patch('sys.stdout', new=io.StringIO()) as fake_out:
        utils.print_header("Test Header", count=1, use_color=True)
        output = fake_out.getvalue()
        assert "Test Header" in output
        assert "(1 match)" in output
        assert "\033[" in output
        assert "==========" in output

    buf = io.StringIO()
    utils.print_header("Search", count="Showing 1 of 2", file=buf, use_color=False)
    output = buf.getvalue()
    assert "Search (Showing 1 of 2)" in output
    assert "\033[" not in output
    assert "=======" in output

    buf = io.StringIO()
    utils.print_header("Results", count=2, file=buf, use_color=False)
    assert "(2 matches)" in buf.getvalue()

    mock_file = MagicMock(spec=io.TextIOBase)
    mock_file.isatty.return_value = True
    utils.print_header("AutoColor", count=None, file=mock_file, use_color=None)
    assert mock_file.isatty.called

def test_card_pt_fallback_and_suppression():
    src_battle = {
        "name": "Test Battle",
        "types": ["Battle"],
        "pt": "5",
        "rarity": "rare"
    }
    card = cardlib.Card(src_battle)
    assert utils.from_unary_single(card.loyalty) == 5
    assert card.pt == ""

    src_pw = {
        "name": "Test PW",
        "types": ["Planeswalker"],
        "pt": "3",
        "rarity": "mythic"
    }
    card = cardlib.Card(src_pw)
    assert utils.from_unary_single(card.loyalty) == 3
    assert card.pt == ""

    src_creature = {
        "name": "Test Creature",
        "types": ["Creature"],
        "pt": "2/2",
        "rarity": "common"
    }
    card = cardlib.Card(src_creature)
    assert card.pt == utils.to_unary("2") + "/" + utils.to_unary("2")
    assert card.loyalty == ""

def test_datalib_plimit_short_string():
    res = datalib.plimit("hello", 10)
    assert res == "hello"

    ansi_str = utils.colorize("red", utils.Ansi.RED) + " text"
    res = datalib.plimit(ansi_str, 20)
    assert "red" in res
    assert "text" in res
    assert "\033[" in res

def test_mana_translate_fallback_branch():
    res = utils.mana_translate("{1.5}")
    assert res == "{{1.5}}"

def test_text_unpass_1_choice_fallback_branch():
    s = "[& = ability]"
    res = transforms.text_unpass_1_choice(s)
    assert "ability" in res
