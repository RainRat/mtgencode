import pytest
from lib.manalib import Manacost, Manatext
from lib.utils import mana_translate, mana_untranslate

def test_mana_translate():
    assert mana_translate("{W}{U}{B}{R}{G}") == "{WWUUBBRRGG}"
    assert mana_translate("{10}") == "{^^^^^^^^^^}"
    assert mana_translate("") == "{}"

def test_mana_untranslate():
    assert mana_untranslate("{WWUUBBRRGG}") == "{W}{U}{B}{R}{G}"
    assert mana_untranslate("{^^^^^^^^^^}") == "{10}"
    assert mana_untranslate("{}") == "{0}"

def test_manacost_initialization():
    manacost = Manacost("{WWUUBBRRGG}")
    assert manacost.cmc == 5
    assert manacost.colors == "BGRUW"
    assert manacost.valid

def test_manatext_initialization():
    manatext = Manatext("Pay {1} {W} to gain 2 life.", fmt="json")
    assert len(manatext.costs) == 2
    assert manatext.costs[0].cmc == 1
    assert manatext.costs[1].cmc == 1
    assert manatext.costs[1].colors == "W"
    assert manatext.valid

def test_check_colors():
    m = Manacost("{WWUUBBRRGG}") # WUBRG
    assert m.colors == "BGRUW"

    # Check subset
    assert m.check_colors("W")
    assert m.check_colors("U")
    assert m.check_colors("WU")
    assert m.check_colors("BGRUW")

    # Check not subset
    m2 = Manacost("{WW}") # W
    assert m2.colors == "W"
    assert m2.check_colors("W")
    assert not m2.check_colors("U")
    assert not m2.check_colors("WU")

    m3 = Manacost("{UU}") # U
    assert m3.colors == "U"
    assert not m3.check_colors("W")

    # Empty
    m_empty = Manacost("{}")
    assert m_empty.colors == ""
    assert not m_empty.check_colors("W")
    assert m_empty.check_colors("") # Empty string is subset of empty string
