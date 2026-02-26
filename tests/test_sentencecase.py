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

def test_sentencecase_with_this_marker():
    # @ deals 2 damage. -> Grizzly Bears deals 2 damage.
    input_text = f"{utils.this_marker} deals 2 damage."
    # We want it to stay as is, because @ will be replaced by a capitalized name.
    result = sentencecase(input_text)
    assert result == f"{utils.this_marker} deals 2 damage."

def test_sentencecase_with_x_marker():
    # X is the number of... -> X is the number of...
    input_text = f"{utils.x_marker} is the number of cards in your hand."
    result = sentencecase(input_text)
    assert result == f"{utils.x_marker} is the number of cards in your hand."

def test_sentencecase_choice_options():
    # Options in choice blocks should be capitalized.
    # Choice format: [&^ =option 1 =option 2]
    input_text = "[&^ =deal 3 damage =draw a card]"
    expected = "[&^ =Deal 3 damage =Draw a card]"
    assert sentencecase(input_text) == expected
