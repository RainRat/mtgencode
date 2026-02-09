import pytest
from lib.cardlib import sentencecase
from lib import utils

def test_sentencecase_basic():
    assert sentencecase("hello world") == "Hello world"
    assert sentencecase("this is a test. another test.") == "This is a test. Another test."

def test_sentencecase_with_activated_ability():
    assert sentencecase("tap: do something.") == "Tap: Do something."
    assert sentencecase("{t}: add {w}.") == "{T}: Add {w}."

def test_sentencecase_preserves_empty_lines():
    # utils.newline is '\\'
    input_text = f"line 1{utils.newline}{utils.newline}line 2"
    expected = f"Line 1{utils.newline}{utils.newline}Line 2"
    assert sentencecase(input_text) == expected

def test_sentencecase_trailing_newline():
    input_text = f"line 1{utils.newline}"
    expected = f"Line 1{utils.newline}"
    assert sentencecase(input_text) == expected

def test_sentencecase_leading_newline():
    input_text = f"{utils.newline}line 1"
    expected = f"{utils.newline}Line 1"
    assert sentencecase(input_text) == expected

def test_sentencecase_multiple_newlines():
    input_text = f"line 1{utils.newline}{utils.newline}{utils.newline}line 2"
    expected = f"Line 1{utils.newline}{utils.newline}{utils.newline}Line 2"
    assert sentencecase(input_text) == expected

def test_sentencecase_only_newlines():
    input_text = f"{utils.newline}{utils.newline}"
    expected = f"{utils.newline}{utils.newline}"
    assert sentencecase(input_text) == expected
