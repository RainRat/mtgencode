import sys
from unittest.mock import patch
import os

# Ensure lib is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../lib')))

from manalib import Manacost, Manatext
import utils

def test_manacost_initialization_delimiters():
    # Coverage for lines 53-54
    m = Manacost("invalid")
    assert not m.parsed
    assert not m.valid

def test_manacost_format_none():
    # Coverage for line 105
    m = Manacost("")
    assert m.format() == ""

def test_manacost_str():
    m = Manacost("{WWUUBBRRGG}")
    assert str(m) == "{W}{U}{B}{R}{G}"

def test_manatext_str():
    src = "Pay {X}."
    mt = Manatext(src, fmt='json')
    assert str(mt) == src

def test_manacost_none_methods():
    m = Manacost("")
    assert m.encode() == ""
    assert m.vectorize() == ""
    # line 115
    assert m.encode(randomize=True) == ""
    # line 126
    assert m.vectorize(delimit=True) == ""

def test_manacost_alt_symbols():
    # {UW} is the alternative order for {WU}
    m = Manacost("{UW}")
    assert m.valid
    assert m.symbols['WU'] == 1
    assert m.allsymbols['UW'] == 1

def test_manacost_invalid_symbols():
    m = Manacost("{?}")
    assert not m.valid

def test_manacost_unary_marker():
    with patch('utils.mana_unary_marker', '&'):
        m = Manacost("{&}")
        assert m.valid
        assert m.sequence == ['&']

def test_manacost_encode_randomize():
    # Coverage for line 118-120
    m = Manacost("{WWUU}")
    encoded = m.encode(randomize=True)
    assert len(encoded) == 6
    assert encoded.startswith("{")
    assert encoded.endswith("}")
    # symbols are WW, UU
    assert "WW" in encoded
    assert "UU" in encoded

def test_manacost_vectorize_modes():
    # Coverage for lines 127-133
    m = Manacost("{WWUU}")
    # sorted sequence: UU, WW
    assert m.vectorize(delimit=False) == "UU WW"
    assert m.vectorize(delimit=True) == "(UU) (WW)"

def test_manatext_raw_format():
    src = "Cast {WWUUBBRRGG}."
    mt = Manatext(src, fmt='raw')
    assert mt.valid
    assert len(mt.costs) == 1

def test_manatext_invalid_cost():
    mt = Manatext("Cost {W}.", fmt='raw')
    assert not mt.valid

def test_manatext_leftover_delimiters():
    # Coverage for line 168
    mt = Manatext("Text with { leftover")
    assert not mt.valid

def test_manatext_format_html_newline():
    mt = Manatext("Line 1\nLine 2")
    formatted = mt.format(for_html=True)
    assert "Line 1<br>\nLine 2" in formatted

def test_manatext_encode_vectorize():
    # Coverage for lines 185-189 and 192-213
    mt = Manatext("Cast {1}{W}.", fmt='json')
    assert mt.encode() == "Cast {^WW}."
    vec = mt.vectorize()
    assert "WW ^" in vec
    assert "Cast" in vec

    # Text with special characters for vectorize
    mt2 = Manatext("Pay {W}: T, Q; .", fmt='json')
    # tap_marker is T, untap_marker is Q
    vec2 = mt2.vectorize()
    assert "WW" in vec2
    assert ":" in vec2
    assert "T" in vec2
    assert "Q" in vec2
    assert "." in vec2

def test_manacost_cmc_special():
    # Coverage for lines 89 (mana_2 in sym)
    m = Manacost("{2W}")
    assert m.cmc == 2
