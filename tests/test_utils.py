import pytest
from lib import utils
from lib import config
from lib.utils import to_unary, from_unary

# --- Unary Number Conversion (Original Tests) ---

def test_to_unary_simple():
    assert to_unary("1") == "&^"
    assert to_unary("5") == "&^^^^^"
    assert to_unary("a 1 b 2 c 3") == "a &^ b &^^ c &^^^"

def test_from_unary_simple():
    assert from_unary("&^") == "1"
    assert from_unary("&^^^^^") == "5"
    assert from_unary("a &^ b &^^ c &^^^") == "a 1 b 2 c 3"

def test_to_unary_empty():
    assert to_unary("") == ""

def test_from_unary_empty():
    assert from_unary("") == ""

def test_to_unary_no_numbers():
    assert to_unary("abc") == "abc"

def test_from_unary_no_unary():
    assert from_unary("abc") == "abc"

def test_to_unary_zero():
    assert to_unary("0") == "&"

def test_to_unary_capped(capsys):
    # unary_max is 20
    large_num = "21"
    expected = "&" + "^" * 20

    # Test without warn
    assert to_unary(large_num) == expected
    captured = capsys.readouterr()
    assert captured.out == ""

    # Test with warn
    assert to_unary(large_num, warn=True) == expected
    captured = capsys.readouterr()
    # to_unary(..., warn=True) prints 's' (the whole input string), not just 'n'
    assert large_num in captured.out

def test_to_unary_exceptions():
    # 1000000 -> 1000000 (example exception if it was there, but it's not by default)
    # Let's check what's in config.unary_exceptions
    from lib import config
    for k, v in config.unary_exceptions.items():
        assert to_unary(str(k)) == v

def test_from_unary_zero():
    assert from_unary("&") == "0"

# --- Unicode / ASCII Conversion ---

def test_to_ascii():
    # Test common replacements
    assert utils.to_ascii("\u2014") == config.dash_marker
    assert utils.to_ascii("\u2022") == config.bullet_marker
    assert utils.to_ascii("\u2019") == "'"
    assert utils.to_ascii("\u2018") == "'"
    assert utils.to_ascii("\u2212") == '-'

    # Test accented characters
    assert utils.to_ascii("\xe6") == 'ae'
    assert utils.to_ascii("\xfb") == 'u'
    assert utils.to_ascii("\xfa") == 'u'
    assert utils.to_ascii("\xfc") == 'u'
    assert utils.to_ascii("\xe9") == 'e'
    assert utils.to_ascii("\xe1") == 'a'
    assert utils.to_ascii("\xe0") == 'a'
    assert utils.to_ascii("\xe2") == 'a'
    assert utils.to_ascii("\xf6") == 'o'
    assert utils.to_ascii("\xed") == 'i'

    # Test special math/greek
    assert utils.to_ascii("\u03c0") == 'pi'
    assert utils.to_ascii("\xae") == 'r'
    assert utils.to_ascii("\xbd") == '1/2'
    assert utils.to_ascii("\u221e") == 'inf'
    assert utils.to_ascii("\u2610") == 'na'

    # Test mixed string
    input_str = "Card\u2014Name \u2022 Ability"
    expected = f"Card{config.dash_marker}Name {config.bullet_marker} Ability"
    assert utils.to_ascii(input_str) == expected

# --- Mana Symbol Encoding ---

def test_mana_sym_to_encoding():
    # Single char symbols are doubled
    assert utils.mana_sym_to_encoding('W') == 'WW'
    assert utils.mana_sym_to_encoding('U') == 'UU'
    # Multi char symbols are kept as is
    assert utils.mana_sym_to_encoding('2W') == '2W'
    assert utils.mana_sym_to_encoding('WP') == 'WP'

    # Invalid symbol
    with pytest.raises(ValueError):
        utils.mana_sym_to_encoding('INVALID')

def test_mana_sym_to_json():
    # Single char
    assert utils.mana_sym_to_json('W') == '{W}'
    # Multi char (hybrid) -> 3 chars encoded
    # '2W' -> '{2/W}'
    assert utils.mana_sym_to_json('2W') == '{2/W}'
    # 'WU' -> '{W/U}'
    assert utils.mana_sym_to_json('WU') == '{W/U}'

    # Invalid symbol
    with pytest.raises(ValueError):
        utils.mana_sym_to_json('INVALID')

def test_mana_sym_to_forum():
    # Single char
    assert utils.mana_sym_to_forum('W') == 'W'
    # Hybrid
    # The code does NOT insert slashes for forum output, unlike JSON output
    assert utils.mana_sym_to_forum('WU') == '{WU}'
    # Alt symbol (reverse order)
    # 'UW' is an alt symbol for 'WU'. It should be normalized to '{WU}'
    assert utils.mana_sym_to_forum('UW') == '{WU}'

    with pytest.raises(ValueError):
        utils.mana_sym_to_forum('INVALID')

# --- Direct Mana Encoding/Decoding ---

def test_mana_encode_direct():
    assert utils.mana_encode_direct('{W}') == 'WW'
    assert utils.mana_encode_direct('{W/U}') == 'WU'

    with pytest.raises(ValueError):
        utils.mana_encode_direct('{INVALID}')

def test_mana_decode_direct():
    assert utils.mana_decode_direct('WW') == '{W}'
    assert utils.mana_decode_direct('WU') == '{W/U}'

    with pytest.raises(ValueError):
        utils.mana_decode_direct('INVALID')

def test_mana_decode_direct_forum():
    # 'WW' encodes 'W'. mana_sym_to_forum('W') -> 'W'
    assert utils.mana_decode_direct_forum('WW') == 'W'
    # 'WU' encodes 'WU'. mana_sym_to_forum('WU') -> '{WU}'
    assert utils.mana_decode_direct_forum('WU') == '{WU}'

    with pytest.raises(ValueError):
        utils.mana_decode_direct_forum('INVALID')

# --- Symbol Translation (Tap/Untap) ---

def test_to_symbols():
    # {T} -> T
    # {Q} -> Q
    # Case insensitive inputs from JSON
    assert utils.to_symbols("{T}") == config.tap_marker
    assert utils.to_symbols("{t}") == config.tap_marker
    assert utils.to_symbols("{Q}") == config.untap_marker
    assert utils.to_symbols("{q}") == config.untap_marker

    assert utils.to_symbols("Tap {T} add {W}") == f"Tap {config.tap_marker} add {{W}}"

def test_from_symbols():
    # T -> {T}
    # Q -> {Q}
    t = config.tap_marker
    q = config.untap_marker

    # Default (JSON)
    assert utils.from_symbols(f"{t}") == "{T}"
    assert utils.from_symbols(f"{q}") == "{Q}"

    # Forum
    assert utils.from_symbols(f"{t}", for_forum=True) == "[mana]T[/mana]"
    assert utils.from_symbols(f"{q}", for_forum=True) == "[mana]Q[/mana]"

    # HTML
    assert utils.from_symbols(f"{t}", for_html=True) == "<img class='mana-T'>"
    assert utils.from_symbols(f"{q}", for_html=True) == "<img class='mana-Q'>"

# --- Full Mana String Translation ---

def test_to_mana():
    # Converts JSON mana strings to internal encoded format
    # {W}{U} -> {WWUU}
    assert utils.to_mana("{W}{U}") == "{WWUU}"
    # {2/W} -> {2W}
    assert utils.to_mana("{2/W}") == "{2W}"
    # Numbers
    # {1} -> {^} (unary 1, no marker because mana_unary_marker is empty)
    assert utils.to_mana("{1}") == "{^}"
    assert utils.to_mana("{10}") == "{^^^^^^^^^^}"

    # Mixed case input
    assert utils.to_mana("{w}{u}") == "{WWUU}"

def test_from_mana():
    # Converts internal encoded format back to JSON
    # {WWUU} -> {W}{U}
    assert utils.from_mana("{WWUU}") == "{W}{U}"
    # {2W} -> {2/W}
    assert utils.from_mana("{2W}") == "{2/W}"
    # Unary numbers
    # {^} -> {1}
    assert utils.from_mana("{^}") == "{1}"

    # Empty
    assert utils.from_mana("{}") == "{0}"

    # Forum output
    # {WW} -> [mana]W[/mana]
    assert utils.from_mana("{WW}", for_forum=True) == "[mana]W[/mana]"

    # {^WW} -> {1}{W}
    # colorless_total = 1
    # jmanastr = 'W'
    # -> [mana]1W[/mana]
    assert utils.from_mana("{^WW}", for_forum=True) == "[mana]1W[/mana]"

# --- ANSI Coloring ---

def test_ansi_constants():
    assert utils.Ansi.RESET == '\033[0m'
    assert utils.Ansi.BOLD == '\033[1m'
    assert utils.Ansi.RED == '\033[91m'
    assert utils.Ansi.CYAN == '\033[96m'

def test_colorize_simple():
    text = "Hello"
    color = utils.Ansi.RED
    expected = f"{color}Hello{utils.Ansi.RESET}"
    assert utils.colorize(text, color) == expected

def test_colorize_empty():
    assert utils.colorize("", utils.Ansi.RED) == ""
    assert utils.colorize(None, utils.Ansi.RED) is None

def test_colorize_combined():
    text = "Bold Red"
    color = utils.Ansi.BOLD + utils.Ansi.RED
    expected = f"\033[1m\033[91mBold Red\033[0m"
    assert utils.colorize(text, color) == expected
