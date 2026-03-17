from lib import utils
from lib import config

def test_from_unary_single_standard_conversion():
    assert utils.from_unary_single("&^") == 1
    assert utils.from_unary_single("&^^^^^") == 5

def test_from_unary_single_numeric_strings():
    assert utils.from_unary_single("10") == 10
    assert utils.from_unary_single("2.5") == 2.5

def test_from_unary_single_config_exceptions():
    for k, v in config.unary_exceptions.items():
        assert utils.from_unary_single(v) == k

def test_from_unary_single_handles_none_and_empty():
    assert utils.from_unary_single(None) is None
    assert utils.from_unary_single("") is None

def test_from_unary_single_handles_unparseable():
    assert utils.from_unary_single("star") is None
    assert utils.from_unary_single("*") is None

def test_get_color_color_single_colors():
    Ansi = utils.Ansi
    assert Ansi.get_color_color('W') == Ansi.BOLD + Ansi.WHITE
    assert Ansi.get_color_color('U') == Ansi.BOLD + Ansi.CYAN
    assert Ansi.get_color_color('B') == Ansi.BOLD + Ansi.MAGENTA
    assert Ansi.get_color_color('R') == Ansi.BOLD + Ansi.RED
    assert Ansi.get_color_color('G') == Ansi.BOLD + Ansi.GREEN

def test_get_color_color_colorless_indicators():
    Ansi = utils.Ansi
    assert Ansi.get_color_color('A') == Ansi.BOLD + Ansi.CYAN
    assert Ansi.get_color_color('Colorless') == Ansi.BOLD + Ansi.CYAN
    assert Ansi.get_color_color('Land') == Ansi.BOLD + Ansi.CYAN

def test_get_color_color_multi_and_hybrid():
    Ansi = utils.Ansi
    assert Ansi.get_color_color('M') == Ansi.BOLD + Ansi.YELLOW
    assert Ansi.get_color_color('WU') == Ansi.BOLD + Ansi.YELLOW
    assert Ansi.get_color_color('WUBRG') == Ansi.BOLD + Ansi.YELLOW
    assert Ansi.get_color_color('2/W') == Ansi.BOLD + Ansi.YELLOW
    assert Ansi.get_color_color('G/W/P') == Ansi.BOLD + Ansi.YELLOW

def test_get_color_color_false_positives():
    Ansi = utils.Ansi
    # Should NOT be yellow
    assert Ansi.get_color_color('GLITCH') == Ansi.BOLD
    assert Ansi.get_color_color('UNKNOWN') == Ansi.BOLD
    assert Ansi.get_color_color('SWAMP') == Ansi.BOLD
    assert Ansi.get_color_color('MOUNTAIN') == Ansi.BOLD

def test_get_color_color_edge_cases():
    Ansi = utils.Ansi
    assert Ansi.get_color_color(None) == Ansi.BOLD
    assert Ansi.get_color_color('') == Ansi.BOLD
    assert Ansi.get_color_color('X') == Ansi.BOLD

def test_get_scryfall_url_generation():
    assert utils.get_scryfall_url('LEA', '1') == 'https://scryfall.com/card/lea/1'
    assert utils.get_scryfall_url('lea', '1') == 'https://scryfall.com/card/lea/1'

def test_get_scryfall_image_url_versions():
    assert utils.get_scryfall_image_url('LEA', '1') == 'https://api.scryfall.com/cards/lea/1?format=image&version=normal'
    assert utils.get_scryfall_image_url('lea', '1', version='small') == 'https://api.scryfall.com/cards/lea/1?format=image&version=small'

def test_get_scryfall_urls_missing_metadata():
    assert utils.get_scryfall_url(None, '1') is None
    assert utils.get_scryfall_url('lea', None) is None
    assert utils.get_scryfall_image_url(None, '1') is None
    assert utils.get_scryfall_image_url('lea', None) is None
