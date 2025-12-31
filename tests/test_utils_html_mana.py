import pytest
from lib import utils

def test_from_mana_html_simple():
    # {W} -> <img class='mana-W'>
    assert utils.from_mana("{WW}", for_html=True) == "<img class='mana-W'>"
    # {U} -> <img class='mana-U'>
    assert utils.from_mana("{UU}", for_html=True) == "<img class='mana-U'>"

def test_from_mana_html_multiple():
    # {W}{U} -> <img class='mana-W'><img class='mana-U'>
    assert utils.from_mana("{WWUU}", for_html=True) == "<img class='mana-W'><img class='mana-U'>"

def test_from_mana_html_hybrid():
    # {W/U} (hybrid) -> <img class='mana-W-U'>
    assert utils.from_mana("{WU}", for_html=True) == "<img class='mana-W-U'>"

def test_from_mana_html_numeric():
    # {1} -> <img class='mana-1'>
    assert utils.from_mana("{^}", for_html=True) == "<img class='mana-1'>"
    # {10} -> <img class='mana-10'>
    assert utils.from_mana("{^^^^^^^^^^}", for_html=True) == "<img class='mana-10'>"

def test_from_mana_html_mixed_numeric_color():
    # {1}{W} -> <img class='mana-1'><img class='mana-W'>
    assert utils.from_mana("{^WW}", for_html=True) == "<img class='mana-1'><img class='mana-W'>"

def test_from_mana_html_repeated_hybrid():
    # {W/U}{W/U} -> <img class='mana-W-U'><img class='mana-W-U'>
    assert utils.from_mana("{WUWU}", for_html=True) == "<img class='mana-W-U'><img class='mana-W-U'>"

def test_from_mana_html_empty():
    # {} -> <img class='mana-0'>
    assert utils.from_mana("{}", for_html=True) == "<img class='mana-0'>"

def test_from_mana_html_phyrexian():
    # {P} -> <img class='mana-P'>
    assert utils.from_mana("{PP}", for_html=True) == "<img class='mana-P'>"
    # {W/P} -> <img class='mana-W-P'>
    assert utils.from_mana("{WP}", for_html=True) == "<img class='mana-W-P'>"

def test_from_mana_html_2monocolor():
    # {2/W} -> <img class='mana-2-W'>
    assert utils.from_mana("{2W}", for_html=True) == "<img class='mana-2-W'>"
