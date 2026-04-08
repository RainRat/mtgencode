import sys
import io
from unittest.mock import patch, MagicMock
import pytest
from lib import utils

def test_numeric_filter_range():
    nf = utils.NumericFilter("1-5")
    assert nf.mode == 'range'
    assert nf.val == 1.0
    assert nf.val2 == 5.0
    assert nf.evaluate(1)
    assert nf.evaluate(3)
    assert nf.evaluate(5)
    assert not nf.evaluate(0)
    assert not nf.evaluate(6)

def test_numeric_filter_invalid_string():
    with pytest.raises(ValueError):
        utils.NumericFilter("not-a-filter")

def test_numeric_filter_evaluate_edge_cases():
    nf = utils.NumericFilter("5")
    assert nf.evaluate("5")
    assert nf.evaluate(5.0)
    assert not nf.evaluate(None)
    assert not nf.evaluate("not-a-number")

def test_mana_untranslate_colorless_ansi():
    encoded = "{" + utils.unary_counter + "}"
    res = utils.mana_untranslate(encoded, ansi_color=True)
    assert "\033[1m{1}\033[0m" == res

def test_print_operation_summary_success_tty():
    with patch('sys.stderr', new=io.StringIO()) as fake_stderr:
        fake_stderr.isatty = lambda: True
        utils.print_operation_summary("TestOp", 10, 0)
        output = fake_stderr.getvalue()
        assert "TestOp complete: 10 cards processed." in output
        assert "\033[1m\033[92m" in output

def test_print_operation_summary_failure_tty():
    with patch('sys.stderr', new=io.StringIO()) as fake_stderr:
        fake_stderr.isatty = lambda: True
        utils.print_operation_summary("TestOp", 8, 2)
        output = fake_stderr.getvalue()
        assert "TestOp complete:" in output
        assert "8 cards successfully processed." in output
        assert "2 cards failed." in output
        assert "\033[1m\033[91m" in output

def test_print_operation_summary_no_tty():
    with patch('sys.stderr', new=io.StringIO()) as fake_stderr:
        fake_stderr.isatty = lambda: False
        utils.print_operation_summary("TestOp", 10, 0)
        output = fake_stderr.getvalue()
        assert "TestOp complete: 10 cards processed." in output
        assert "\033[" not in output

def test_print_operation_summary_quiet():
    with patch('sys.stderr', new=io.StringIO()) as fake_stderr:
        utils.print_operation_summary("TestOp", 10, 0, quiet=True)
        assert fake_stderr.getvalue() == ""
