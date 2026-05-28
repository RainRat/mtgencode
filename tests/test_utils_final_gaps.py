import io
import sys
import re
from unittest.mock import MagicMock, patch
from lib import utils
from lib import config

def test_to_unary_warn_branch():
    with patch('builtins.print') as mocked_print:
        # unary_max is 20 by default. 21 should trigger the warning if warn=True
        utils.to_unary("21", warn=True)
        mocked_print.assert_called_once_with("21")

def test_from_unary_with_exceptions():
    # thirty -> 30
    assert utils.from_unary("thirty") == "30"
    # thirty-five -> 35 (via dash_marker)
    assert utils.from_unary("twenty~five") == "25"

def test_mana_translate_fixes():
    # Test word-based exception in mana
    # {thirty} -> {^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^}
    # (mana_unary_marker is empty)
    expected = "{" + utils.mana_unary_marker + utils.unary_counter * 30 + "}"
    assert utils.mana_translate("{thirty}") == expected

    # Test case insensitivity for word-based exception
    assert utils.mana_translate("{THIRTY}") == expected

    # Test unknown token matching the regex (e.g. {unknown})
    # Should return {unknown} and NOT {{unknown}}
    assert utils.mana_translate("{unknown}") == "{unknown}"

def test_print_header_coverage():
    # Test with string count (non-int)
    f = io.StringIO()
    utils.print_header("Test", count="Many", file=f, use_color=False)
    output = f.getvalue()
    assert "  Test (Many)" in output
    assert "  ===========" in output

    # Test use_color=True with int count
    f = io.StringIO()
    # Mock colorize to just return the text to avoid messy ANSI checks here
    # or just check that they are present.
    utils.print_header("Test", count=1, file=f, use_color=True)
    output = f.getvalue()
    assert "Test" in output
    assert "(1 match)" in output
    # ANSI escape for Cyan is \033[96m
    assert "\033[96m" in output

    # Test default use_color (file.isatty() fallback)
    f = io.StringIO()
    f.isatty = lambda: True
    utils.print_header("TTY", count=0, file=f)
    output = f.getvalue()
    assert "\033[96m" in output

def test_print_operation_summary_quiet():
    # Should return early and not print anything
    with patch('sys.stderr', new=io.StringIO()) as mocked_stderr:
        utils.print_operation_summary("Test", 1, 0, quiet=True)
        assert mocked_stderr.getvalue() == ""

def test_print_operation_summary_failures():
    # Test with failures and color (mocked TTY)
    with patch('sys.stderr', new=io.StringIO()) as mocked_stderr:
        mocked_stderr.isatty = lambda: True
        utils.print_operation_summary("TestOp", 10, 5, quiet=False)
        output = mocked_stderr.getvalue()
        assert "TestOp complete:" in output
        assert "10 cards successfully processed." in output
        assert "5 cards failed." in output
        # ANSI Bold Cyan for header
        assert "\033[1m\033[96m" in output
        # ANSI Green for success
        assert "\033[92m" in output
        # ANSI Bold Red for failures
        assert "\033[1m\033[91m" in output

def test_mana_translate_raw_string():
    # Test passing a string without braces to mana_translate
    # (now it always wraps in braces if it's not None)
    assert utils.mana_translate("no_braces") == "{no_braces}"

def test_print_header_default_file():
    # Test print_header with file=None to hit line 725
    with patch('sys.stdout', new=io.StringIO()) as mocked_stdout:
        utils.print_header("DefaultFile", use_color=False)
        assert "DefaultFile" in mocked_stdout.getvalue()

def test_mana_translate_none():
    assert utils.mana_translate(None) is None

def test_mana_translate_unknown_braced():
    # Hit line 465 by having replace_token return 'inner' for unknown token
    # {unknown} matches mana_json_regex in to_mana, but mana_translate_regex
    # doesn't match 'unknown' inside it if we don't handle it.
    # Actually, mana_translate_regex only matches standard symbols.
    # So re.sub(mana_translate_regex, ...) does NOTHING to '{unknown}'
    # then processed = '{unknown}'
    # then it strips braces -> 'unknown'
    # then it wraps -> '{unknown}'
    assert utils.mana_translate("{unknown}") == "{unknown}"

def test_mana_translate_complex():
    # Test a case where replace_token IS called but returns 'inner'
    # This happens if we match mana_decimal_regex or mana_unary_regex
    # but for some reason it doesn't fall into the i = int(inner) etc. branches.
    # Actually, those regexes ARE restrictive.
    # {0} -> inner is "0" -> isdigit -> returns "^" * 0 -> empty string
    assert utils.mana_translate("{0}") == "{}"

def test_mana_translate_forced_fallback():
    # Force the fallback branch in replace_token (line 466)
    # This requires a match from mana_translate_regex that doesn't
    # satisfy any of the if/elif conditions in replace_token.

    # We can temporarily patch one of the regex components to include something "weird"
    weird_regex = re.compile(r'\{weird\}')
    with patch('lib.utils.mana_translate_regex', weird_regex):
        # Now "{weird}" matches, but inner is "weird"
        # "weird" is not digit, not in exceptions, doesn't start with unary_marker
        assert utils.mana_translate("{weird}") == "{weird}"
