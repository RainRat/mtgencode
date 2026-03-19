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
    assert Ansi.get_color_color('WU') == Ansi.BOLD + Ansi.YELLOW
    assert Ansi.get_color_color('WUBRG') == Ansi.BOLD + Ansi.YELLOW

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

def test_from_symbols_ansi_color():
    t = config.tap_marker
    res = utils.from_symbols(t, ansi_color=True)
    # colorize(res, Ansi.BOLD + Ansi.YELLOW) -> \033[1m\033[93m{T}\033[0m
    assert "\033[1m\033[93m{T}\033[0m" == res

def test_from_symbols_no_ansi_color():
    t = config.tap_marker
    res = utils.from_symbols(t, ansi_color=False)
    assert "{T}" == res

def test_numeric_filter_evaluation_operators():
    # !=
    nf_not_zero = utils.NumericFilter("!= 0")
    assert nf_not_zero.evaluate(5)
    assert not nf_not_zero.evaluate(0)

    # ==
    nf_equal_four = utils.NumericFilter("== 4")
    assert nf_equal_four.evaluate(4)
    assert not nf_equal_four.evaluate(3)

def test_numeric_filter_evaluation_invalid_types():
    nf = utils.NumericFilter("5")
    # Trigger except (ValueError, TypeError)
    # float([]) or float({}) should raise TypeError
    assert not nf.evaluate([])
    assert not nf.evaluate({})

def test_from_mana_ansi_color():
    # Primary color
    # {WW} -> colorized {W}
    res = utils.from_mana("{WW}", ansi_color=True)
    # get_sym_color('W') -> \033[97m (Ansi.WHITE, NOT bolded)
    assert "\033[97m{W}\033[0m" == res

    # Hybrid/Multi color
    # {WU} -> colorized {W/U}
    res = utils.from_mana("{WU}", ansi_color=True)
    # get_sym_color('WU') -> get_color_color('WU') -> BOLD + YELLOW -> \033[1m\033[93m
    assert "\033[1m\033[93m{W/U}\033[0m" == res

def test_from_mana_no_ansi_color():
    res = utils.from_mana("{WW}", ansi_color=False)
    assert "{W}" == res

    res = utils.from_mana("{WU}", ansi_color=False)
    assert "{W/U}" == res

def test_numeric_filter_evaluation_null_mode():
    nf = utils.NumericFilter("5")
    # Manually set mode to something invalid to attempt hitting the end of evaluate()
    nf.mode = 'INVALID'
    assert nf.evaluate(5) is False
