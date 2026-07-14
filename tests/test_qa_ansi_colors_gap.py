from lib import utils

def test_ansi_get_color_color_symbols_gap():
    Ansi = utils.Ansi
    # 'C' for Colorless and 'S' for Snow should be Cyan
    assert Ansi.get_color_color('C') == Ansi.BOLD + Ansi.CYAN
    assert Ansi.get_color_color('S') == Ansi.BOLD + Ansi.CYAN
    assert Ansi.get_color_color('SNOW') == Ansi.BOLD + Ansi.CYAN

def test_ansi_get_color_color_names_gap():
    Ansi = utils.Ansi
    # Full color names should be mapped correctly
    assert Ansi.get_color_color('WHITE') == Ansi.BOLD + Ansi.WHITE
    assert Ansi.get_color_color('BLUE') == Ansi.BOLD + Ansi.CYAN
    assert Ansi.get_color_color('BLACK') == Ansi.BOLD + Ansi.MAGENTA
    assert Ansi.get_color_color('RED') == Ansi.BOLD + Ansi.RED
    assert Ansi.get_color_color('GREEN') == Ansi.BOLD + Ansi.GREEN

def test_ansi_get_rarity_color_basic_land_gap():
    Ansi = utils.Ansi
    # Basic land rarity should be Bold
    assert Ansi.get_rarity_color('basic land') == Ansi.BOLD
    assert Ansi.get_rarity_color('Basic Land') == Ansi.BOLD
    assert Ansi.get_rarity_color(utils.rarity_basic_land_marker) == Ansi.BOLD
