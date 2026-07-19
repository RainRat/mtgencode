from lib.cardlib import cap
from lib import utils

def test_cap_basic():
    assert cap("hello") == "Hello"

def test_cap_with_mana_at_start():
    assert cap("{2U} remove a counter") == "{2U} Remove a counter"

def test_cap_with_choice_at_start():
    assert cap("[choice] text") == "[Choice] Text"

def test_cap_empty():
    assert cap("") == ""

def test_cap_no_alpha():
    assert cap("{2}") == "{2}"

def test_cap_this_marker():
    assert cap("@ does something") == "@ does something"

def test_cap_reserved_marker():
    assert cap("\v does something") == "\v does something"

def test_cap_mana_and_markers():
    assert cap("{t}: @ does something") == "{T}: @ does something"

def test_cap_only_choice():
    assert cap("[choice]") == "[Choice]"

def test_cap_choice_unclosed():
    assert cap("[abc") == "[Abc"
