import pytest
from lib.utils import to_unary, from_unary

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

def test_from_unary_zero():
    assert from_unary("&") == "0"
