import pytest
import io
import sys
import re
from unittest.mock import MagicMock, patch
from lib import utils
from lib import config
from lib import jdecode
from lib import cardlib

# --- 1. Unary Number Conversion ---

def test_to_unary_simple():
    assert utils.to_unary("1") == "&^"
    assert utils.to_unary("5") == "&^^^^^"
    assert utils.to_unary("a 1 b 2 c 3") == "a &^ b &^^ c &^^^"

def test_from_unary_simple():
    assert utils.from_unary("&^") == "1"
    assert utils.from_unary("&^^^^^") == "5"
    assert utils.from_unary("a &^ b &^^ c &^^^") == "a 1 b 2 c 3"

def test_to_unary_empty():
    assert utils.to_unary("") == ""

def test_from_unary_empty():
    assert utils.from_unary("") == ""

def test_to_unary_no_numbers():
    assert utils.to_unary("abc") == "abc"

def test_from_unary_no_unary():
    assert utils.from_unary("abc") == "abc"

def test_to_unary_zero():
    assert utils.to_unary("0") == "&"

def test_to_unary_capped(capsys):
    # unary_max is 20 by default
    large_num = "21"
    expected = "&" + "^" * 20

    # Test without warn
    assert utils.to_unary(large_num) == expected
    captured = capsys.readouterr()
    assert captured.out == ""

    # Test with warn
    assert utils.to_unary(large_num, warn=True) == expected
    captured = capsys.readouterr()
    assert large_num in captured.out

def test_to_unary_exceptions():
    for k, v in config.unary_exceptions.items():
        assert utils.to_unary(str(k)) == v

def test_from_unary_zero():
    assert utils.from_unary("&") == "0"

def test_from_unary_with_exceptions():
    # thirty -> 30
    assert utils.from_unary("thirty") == "30"
    # twenty~five -> 25 (via dash_marker)
    assert utils.from_unary("twenty~five") == "25"

def test_from_unary_single_conversion():
    assert utils.from_unary_single("&^") == 1
    assert utils.from_unary_single("&^^^^^") == 5
    assert utils.from_unary_single("10") == 10
    assert utils.from_unary_single("2.5") == 2.5
    for k, v in config.unary_exceptions.items():
        assert utils.from_unary_single(v) == k
    assert utils.from_unary_single(None) is None
    assert utils.from_unary_single("") is None
    assert utils.from_unary_single("star") is None

# --- 2. Unicode / ASCII Conversion ---

def test_to_ascii():
    assert utils.to_ascii("\u2014") == config.dash_marker
    assert utils.to_ascii("\u2022") == config.bullet_marker
    assert utils.to_ascii("\u2019") == "'"
    assert utils.to_ascii("\xe6") == 'ae'
    assert utils.to_ascii("\u03c0") == 'pi'
    assert utils.to_ascii("\xbd") == '1/2'
    assert utils.to_ascii("\u221e") == 'inf'

    input_str = "Card\u2014Name \u2022 Ability"
    expected = f"Card{config.dash_marker}Name {config.bullet_marker} Ability"
    assert utils.to_ascii(input_str) == expected

# --- 3. Mana Symbol Encoding and Translation ---

def test_mana_alt():
    assert utils.mana_alt('WU') == 'UW'
    assert utils.mana_alt('W') == 'W'
    with pytest.raises(ValueError):
        utils.mana_alt('INVALID')

def test_mana_sym_to_encoding():
    assert utils.mana_sym_to_encoding('W') == 'WW'
    assert utils.mana_sym_to_encoding('2W') == '2W'
    with pytest.raises(ValueError):
        utils.mana_sym_to_encoding('INVALID')

def test_mana_sym_to_json():
    assert utils.mana_sym_to_json('W') == '{W}'
    assert utils.mana_sym_to_json('2W') == '{2/W}'
    assert utils.mana_sym_to_json('WU') == '{W/U}'
    with pytest.raises(ValueError):
        utils.mana_sym_to_json('INVALID')

def test_mana_sym_to_forum():
    assert utils.mana_sym_to_forum('W') == 'W'
    assert utils.mana_sym_to_forum('WU') == '{WU}'
    assert utils.mana_sym_to_forum('UW') == '{WU}' # Alt symbol normalization
    with pytest.raises(ValueError):
        utils.mana_sym_to_forum('INVALID')

def test_mana_encode_decode_direct():
    assert utils.mana_encode_direct('{W}') == 'WW'
    with pytest.raises(ValueError):
        utils.mana_encode_direct('{INVALID}')

    assert utils.mana_decode_direct('WW') == '{W}'
    with pytest.raises(ValueError):
        utils.mana_decode_direct('INVALID')

    assert utils.mana_decode_direct_forum('WU') == '{WU}'
    assert utils.mana_decode_direct_forum('WW') == 'W'
    with pytest.raises(ValueError):
        utils.mana_decode_direct_forum('INVALID')

def test_unique_string():
    assert utils.unique_string("aabbc") in ["abc", "acb", "bac", "bca", "cab", "cba"]

def test_to_mana_translation():
    assert utils.to_mana("{W}{U}") == "{WWUU}"
    assert utils.to_mana("{2/W}") == "{2W}"
    assert utils.to_mana("{1}") == "{^}"
    assert utils.to_mana("{w}{u}") == "{WWUU}"
    assert utils.to_mana("{&^}") == "{^}"

def test_mana_translate_fixes():
    # Test word-based exception in mana
    expected = "{" + utils.mana_unary_marker + utils.unary_counter * 30 + "}"
    assert utils.mana_translate("{thirty}") == expected
    assert utils.mana_translate("{THIRTY}") == expected
    assert utils.mana_translate("{unknown}") == "{unknown}"
    assert utils.mana_translate("no_braces") == "{no_braces}"
    assert utils.mana_translate(None) is None
    assert utils.mana_translate("{0}") == "{}"

def test_mana_translate_forced_fallback():
    weird_regex = re.compile(r'\{weird\}')
    with patch('lib.utils.mana_translate_regex', weird_regex):
        assert utils.mana_translate("{weird}") == "{weird}"

def test_from_mana_translation():
    assert utils.from_mana("{WWUU}") == "{W}{U}"
    assert utils.from_mana("{2W}") == "{2/W}"
    assert utils.from_mana("{^}") == "{1}"
    assert utils.from_mana("{}") == "{0}"

    # ANSI color
    assert "\033[97m{W}\033[0m" == utils.from_mana("{WW}", ansi_color=True)
    assert "\033[1m\033[93m{W/U}\033[0m" == utils.from_mana("{WU}", ansi_color=True)

    # Forum
    assert utils.from_mana("{WW}", for_forum=True) == "[mana]W[/mana]"
    assert utils.from_mana("{^WW}", for_forum=True) == "[mana]1W[/mana]"

    # HTML
    assert utils.from_mana("{WW}", for_html=True) == "<img class='mana-W'>"
    assert utils.from_mana("{WU}", for_html=True) == "<img class='mana-W-U'>"
    assert utils.from_mana("{^WW}", for_html=True) == "<img class='mana-1'><img class='mana-W'>"
    assert utils.from_mana("{}", for_html=True) == "<img class='mana-0'>"

def test_mana_untranslate_variants():
    # Unknown symbol
    assert utils.mana_untranslate("{?}", for_forum=False) == "{0}"
    # Colorless ANSI
    encoded = "{" + utils.unary_counter + "}"
    assert "\033[1m{1}\033[0m" == utils.mana_untranslate(encoded, ansi_color=True)
    # With unary marker
    old_marker = utils.mana_unary_marker
    try:
        utils.mana_unary_marker = '&'
        assert utils.mana_untranslate("{&^}", for_forum=False) == "{1}"
    finally:
        utils.mana_unary_marker = old_marker

# --- 4. Tap/Untap Symbols ---

def test_tap_untap_symbols():
    t = config.tap_marker
    q = config.untap_marker
    assert utils.to_symbols("{T}") == t
    assert utils.to_symbols("{q}") == q

    assert utils.from_symbols(t) == "{T}"
    assert utils.from_symbols(t, for_forum=True) == "[mana]T[/mana]"
    assert utils.from_symbols(q, for_html=True) == "<img class='mana-Q'>"
    assert "\033[1m\033[93m{T}\033[0m" == utils.from_symbols(t, ansi_color=True)

# --- 5. Type Line Parsing ---

def test_split_types():
    assert utils.split_types("Legendary Creature") == (["Legendary"], ["Creature"])
    assert utils.split_types("Legendary Snow Creature") == (["Legendary", "Snow"], ["Creature"])
    assert utils.split_types("Artifact Creature") == ([], ["Artifact", "Creature"])
    assert utils.split_types("Basic") == (["Basic"], [])
    assert utils.split_types("") == ([], [])

def test_parse_type_line():
    assert utils.parse_type_line("Creature \u2014 Goblin") == ([], ["Creature"], ["Goblin"])
    assert utils.parse_type_line("Creature \u2013 Elf Warrior") == ([], ["Creature"], ["Elf", "Warrior"])
    assert utils.parse_type_line("Artifact - Equipment") == ([], ["Artifact"], ["Equipment"])
    assert utils.parse_type_line("Instant") == ([], ["Instant"], [])
    assert utils.parse_type_line("") == ([], [], [])
    assert utils.parse_type_line(None) == ([], [], [])
    assert utils.parse_type_line("Creature \u2014 Goblin \u2014 Warrior") == ([], ["Creature"], ["Goblin", "Warrior"])

# --- 6. ANSI Coloring and Output Utilities ---

def test_colorize():
    assert utils.colorize("Hi", utils.Ansi.RED) == f"{utils.Ansi.RED}Hi{utils.Ansi.RESET}"
    assert utils.colorize("", utils.Ansi.RED) == ""
    assert utils.colorize(None, utils.Ansi.RED) is None

def test_visible_len():
    assert utils.visible_len("hello") == 5
    assert utils.visible_len(utils.colorize("hello", utils.Ansi.RED)) == 5
    assert utils.visible_len("") == 0

def test_get_rarity_color():
    assert utils.Ansi.get_rarity_color('uncommon') == utils.Ansi.BOLD + utils.Ansi.CYAN
    assert utils.Ansi.get_rarity_color('rare') == utils.Ansi.BOLD + utils.Ansi.YELLOW
    assert utils.Ansi.get_rarity_color('mythic') == utils.Ansi.BOLD + utils.Ansi.RED
    assert utils.Ansi.get_rarity_color('special') == utils.Ansi.BOLD + utils.Ansi.MAGENTA
    assert utils.Ansi.get_rarity_color(utils.rarity_mythic_marker) == utils.Ansi.BOLD + utils.Ansi.RED
    assert utils.Ansi.get_rarity_color(None) == utils.Ansi.BOLD

def test_get_color_color():
    Ansi = utils.Ansi
    assert Ansi.get_color_color('W') == Ansi.BOLD + Ansi.WHITE
    assert Ansi.get_color_color('U') == Ansi.BOLD + Ansi.CYAN
    assert Ansi.get_color_color('B') == Ansi.BOLD + Ansi.MAGENTA
    assert Ansi.get_color_color('R') == Ansi.BOLD + Ansi.RED
    assert Ansi.get_color_color('G') == Ansi.BOLD + Ansi.GREEN
    assert Ansi.get_color_color('A') == Ansi.BOLD + Ansi.CYAN
    assert Ansi.get_color_color('Colorless') == Ansi.BOLD + Ansi.CYAN
    assert Ansi.get_color_color('Land') == Ansi.BOLD + Ansi.CYAN
    assert Ansi.get_color_color('WU') == Ansi.BOLD + Ansi.YELLOW
    assert Ansi.get_color_color('M') == Ansi.BOLD + Ansi.YELLOW
    assert Ansi.get_color_color('WUBRG') == Ansi.BOLD + Ansi.YELLOW
    assert Ansi.get_color_color('POWER') == Ansi.BOLD # Not a color
    assert Ansi.get_color_color(None) == Ansi.BOLD
    # Mixed mana string that hits more branches
    assert Ansi.get_color_color('2W') == Ansi.BOLD + Ansi.YELLOW
    assert Ansi.get_color_color('2/P') == Ansi.BOLD # No color characters

def test_print_header(capsys):
    f = io.StringIO()
    utils.print_header("Test", count=1, file=f, use_color=False)
    assert "Test (1 match)" in f.getvalue()

    utils.print_header("Test", count="Many", file=f, use_color=False)
    assert "Test (Many)" in f.getvalue()

    # Color
    f = io.StringIO()
    utils.print_header("Color", count=1, file=f, use_color=True)
    assert "\033[96m" in f.getvalue()

    with patch('sys.stdout', new=io.StringIO()) as mocked_stdout:
        utils.print_header("DefaultFile", use_color=False)
        assert "DefaultFile" in mocked_stdout.getvalue()

    f = io.StringIO()
    f.isatty = lambda: True
    utils.print_header("TTY", count=0, file=f)
    assert "\033[96m" in f.getvalue()

def test_print_operation_summary():
    with patch('sys.stderr', new=io.StringIO()) as mocked_stderr:
        mocked_stderr.isatty = lambda: False
        utils.print_operation_summary("Op", 10, 0, quiet=False)
        assert "Op complete: 10 cards processed." in mocked_stderr.getvalue()

        utils.print_operation_summary("Op", 10, 5, quiet=False)
        assert "5 cards failed." in mocked_stderr.getvalue()

        # Color TTY
        mocked_stderr.truncate(0)
        mocked_stderr.seek(0)
        mocked_stderr.isatty = lambda: True
        utils.print_operation_summary("ColorOp", 10, 0)
        assert "\033[92m" in mocked_stderr.getvalue()

        mocked_stderr.truncate(0)
        mocked_stderr.seek(0)
        utils.print_operation_summary("FailOp", 10, 5)
        assert "\033[91m" in mocked_stderr.getvalue()

        # Quiet mode
        mocked_stderr.truncate(0)
        mocked_stderr.seek(0)
        utils.print_operation_summary("Op", 10, 0, quiet=True)
        assert mocked_stderr.getvalue() == ""

# --- 7. Numeric Filters ---

def test_numeric_filter_parsing():
    nf = utils.NumericFilter("5")
    assert nf.mode == 'exact' and nf.val == 5.0

    nf = utils.NumericFilter("== 3.5")
    assert nf.mode == 'inequality' and nf.op == '==' and nf.val == 3.5

    nf = utils.NumericFilter(">5")
    assert nf.mode == 'inequality' and nf.op == '>'

    nf = utils.NumericFilter("2-4")
    assert nf.mode == 'range' and nf.val == 2.0 and nf.val2 == 4.0

    with pytest.raises(ValueError):
        utils.NumericFilter("abc")

def test_numeric_filter_evaluation():
    nf = utils.NumericFilter("5")
    assert nf.evaluate(5)
    assert nf.evaluate("5")
    assert nf.evaluate("&^^^^^")
    assert not nf.evaluate(4)

    # Operators
    assert utils.NumericFilter("> 5").evaluate(6)
    assert utils.NumericFilter("< 5").evaluate(4)
    assert utils.NumericFilter(">= 5").evaluate(5)
    assert utils.NumericFilter("<= 5").evaluate(5)
    assert utils.NumericFilter("!= 0").evaluate(5)
    assert not utils.NumericFilter("!= 0").evaluate(0)
    assert utils.NumericFilter("== 4").evaluate(4)

    nf = utils.NumericFilter("2-4")
    assert nf.evaluate(3)
    assert not nf.evaluate(5)

    assert not nf.evaluate(None)
    assert not nf.evaluate("star")
    assert not nf.evaluate([])

    # Fallback False
    nf.mode = 'INVALID'
    assert not nf.evaluate(5)

def test_numeric_filter_unary_exceptions():
    assert utils.NumericFilter("30").evaluate("thirty")
    assert utils.NumericFilter("25").evaluate("twenty~five")

def test_jdecode_numeric_filtering_integration(tmp_path):
    import json
    p = tmp_path / "cards.json"
    p.write_text(json.dumps({
        "data": {
            "SET": {
                "name": "Test Set", "code": "SET", "type": "expansion",
                "cards": [
                    {'name': 'Low', 'manaCost': '{1}', 'types': ['Creature'], 'power': '1', 'toughness': '1', 'rarity': 'Common'},
                    {'name': 'High', 'manaCost': '{1}', 'types': ['Creature'], 'power': '5', 'toughness': '5', 'rarity': 'Common'},
                ]
            }
        }
    }))
    cards = jdecode.mtg_open_file(str(p), pows=[">2"])
    assert len(cards) == 1
    assert cards[0].name == 'high'

# --- 8. Scryfall Utilities ---

def test_scryfall_urls():
    assert utils.get_scryfall_url('LEA', '1') == 'https://scryfall.com/card/lea/1'
    assert utils.get_scryfall_image_url('LEA', '1') == 'https://api.scryfall.com/cards/lea/1?format=image&version=normal'
    assert utils.get_scryfall_url(None, '1') is None
    assert utils.get_scryfall_image_url(None, '1') is None
