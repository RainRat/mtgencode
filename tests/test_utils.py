import pytest
import sys
import io
from unittest.mock import patch
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

def test_visible_len():
    # Plain text
    assert utils.visible_len("hello") == 5
    # Colorized text
    assert utils.visible_len(utils.colorize("hello", utils.Ansi.RED)) == 5
    # Combined styles
    assert utils.visible_len(utils.colorize("world", utils.Ansi.BOLD + utils.Ansi.CYAN)) == 5
    # Empty string
    assert utils.visible_len("") == 0
    # Text with embedded codes
    text = f"Part 1 {utils.Ansi.RED}Part 2{utils.Ansi.RESET} Part 3"
    assert utils.visible_len(text) == len("Part 1 Part 2 Part 3")

# --- Extra Coverage for utils.py ---

def test_split_types():
    # Test standard case
    assert utils.split_types("Legendary Creature") == (["Legendary"], ["Creature"])
    # Test multiple supertypes
    assert utils.split_types("Legendary Snow Creature") == (["Legendary", "Snow"], ["Creature"])
    # Test only types
    assert utils.split_types("Artifact Creature") == ([], ["Artifact", "Creature"])
    # Test only supertypes (weird but possible)
    assert utils.split_types("Basic") == (["Basic"], [])
    # Test empty
    assert utils.split_types("") == ([], [])
    # Test with types not in known_supertypes
    assert utils.split_types("World Enchantment") == (["World"], ["Enchantment"])
    # Test multiple types
    assert utils.split_types("Creature Enchantment") == ([], ["Creature", "Enchantment"])

def test_print_operation_summary():
    # Test quiet mode
    with patch('sys.stderr', new=io.StringIO()) as fake_stderr:
        utils.print_operation_summary("Test Op", 10, 0, quiet=True)
        assert fake_stderr.getvalue() == ""

    # Test non-TTY (no color)
    with patch('sys.stderr', new=io.StringIO()) as fake_stderr:
        fake_stderr.isatty = lambda: False
        utils.print_operation_summary("Test Op", 5, 2)
        output = fake_stderr.getvalue()
        assert "Test Op complete:" in output
        assert "5 cards successfully processed" in output
        assert "2 cards failed" in output
        assert "\033[" not in output  # No ANSI codes

    # Test TTY (color)
    with patch('sys.stderr', new=io.StringIO()) as fake_stderr:
        fake_stderr.isatty = lambda: True
        utils.print_operation_summary("Test Op", 5, 2)
        output = fake_stderr.getvalue()
        assert "\033[" in output  # Should have ANSI codes
        assert "Test Op complete:" in output

    # Test no errors case (non-TTY)
    with patch('sys.stderr', new=io.StringIO()) as fake_stderr:
        fake_stderr.isatty = lambda: False
        utils.print_operation_summary("Test Op", 10, 0)
        output = fake_stderr.getvalue()
        assert "No errors encountered" in output
        assert "\033[" not in output

    # Test no errors case (TTY)
    with patch('sys.stderr', new=io.StringIO()) as fake_stderr:
        fake_stderr.isatty = lambda: True
        utils.print_operation_summary("Test Op", 10, 0)
        output = fake_stderr.getvalue()
        assert "No errors encountered" in output
        assert "\033[" in output

def test_mana_alt_extra():
    # len < 2 branch
    # Single character symbols are len 1.
    assert utils.mana_alt('W') == 'W'

    # Invalid symbol
    with pytest.raises(ValueError, match="invalid mana symbol for mana_alt()"):
        utils.mana_alt('INVALID')

    # Standard 2-char symbol
    assert utils.mana_alt('WU') == 'UW'

def test_mana_sym_to_encoding_extra():
    # Invalid symbol
    with pytest.raises(ValueError, match="invalid mana symbol for mana_sym_to_encoding()"):
        utils.mana_sym_to_encoding('INVALID')

def test_mana_untranslate_html():
    # Only colorless
    # {^} -> colorless_total = 1. jmanastr = ''.
    # Should return <img class='mana-1'>
    res = utils.mana_untranslate("{^}", for_html=True)
    assert res == "<img class='mana-1'>"

    # Only colored
    # {WW} -> jmanastr = "<img class='mana-W'>". colorless_total = 0.
    res = utils.mana_untranslate("{WW}", for_html=True)
    assert res == "<img class='mana-W'>"

    # Mixed
    # {^WW} -> colorless_total = 1. jmanastr = "<img class='mana-W'>".
    res = utils.mana_untranslate("{^WW}", for_html=True)
    assert res == "<img class='mana-1'><img class='mana-W'>"

def test_mana_untranslate_forum():
    # Only colorless
    # {^} -> [mana]1[/mana]
    res = utils.mana_untranslate("{^}", for_forum=True)
    assert res == "[mana]1[/mana]"

    # Only colored
    # {WW} -> [mana]W[/mana]
    res = utils.mana_untranslate("{WW}", for_forum=True)
    assert res == "[mana]W[/mana]"

    # Mixed
    # {^WW} -> [mana]1W[/mana]
    res = utils.mana_untranslate("{^WW}", for_forum=True)
    assert res == "[mana]1W[/mana]"

def test_mana_untranslate_unknown_symbol():
    # Hit line 475: idx += 1 if symbol unknown
    # {?} where ? is not in mana_symall_decode
    # mana_untranslate ignores characters it doesn't recognize
    res = utils.mana_untranslate("{?}", for_forum=False)
    assert res == "{0}" # It didn't find any valid symbols or colorless

def test_mana_untranslate_with_unary_marker():
    # Hit line 452 by temporarily setting mana_unary_marker
    old_marker = utils.mana_unary_marker
    try:
        utils.mana_unary_marker = '&'
        # {&^} -> inner is "&^".
        # idx 0: match '&'. idx becomes 1.
        # idx 1: match '^'. idx becomes 2. colorless_total becomes 1.
        res = utils.mana_untranslate("{&^}", for_forum=False)
        assert res == "{1}"
    finally:
        utils.mana_unary_marker = old_marker

def test_mana_translate_unary_branches():
    # Hit lines 432-435 in mana_translate
    res = utils.to_mana("{&^}")
    assert res == "{^}" # &^ is unary 1, becomes encoded ^
