import pytest
from lib.cardlib import Card, fields_from_format, field_name, field_text, field_types
import lib.utils as utils

def test_fields_from_format_labeled_start():
    # '1' is the label for name.
    fmt_labeled = {field_name: '1'}
    fmt_ordered = []
    src_text = "1Grizzly Bears"

    parsed, valid, fields = fields_from_format(src_text, fmt_ordered, fmt_labeled, '|')

    assert fields[field_name][0][1] == "Grizzly Bears"

def test_fields_from_format_labeled_misinterpretation_middle():
    # '9' is the label for text.
    # Digit in the middle should NOT be stripped.
    fmt_labeled = {field_text: '9'}
    fmt_ordered = [field_text]
    src_text = "deals 9 damage."

    parsed, valid, fields = fields_from_format(src_text, fmt_ordered, fmt_labeled, '|')

    # It should match by order because '9' is not at the start.
    assert fields[field_text][0][1].text == "deals 9 damage."

def test_fields_from_format_not_a_label_start():
    # '2' is NOT a label in the default config (though we pass a custom one here to be sure)
    fmt_labeled = {field_name: '1'}
    fmt_ordered = [field_name]
    src_text = "2000 Golems"

    parsed, valid, fields = fields_from_format(src_text, fmt_ordered, fmt_labeled, '|')

    # '2' is not a label, so it remains part of the text.
    assert fields[field_name][0][1] == "2000 Golems"

def test_fields_from_format_multi_char_labels():
    # Test that multi-char labels work (longest match first)
    fmt_labeled = {field_name: 'NAME:', field_text: 'N'}
    fmt_ordered = []

    # Should match 'NAME:' not 'N'
    src_text = "NAME:Grizzly Bears"
    parsed, valid, fields = fields_from_format(src_text, fmt_ordered, fmt_labeled, '|')
    assert fields[field_name][0][1] == "Grizzly Bears"

    # Should match 'N'
    src_text = "NSome text"
    parsed, valid, fields = fields_from_format(src_text, fmt_ordered, fmt_labeled, '|')
    assert fields[field_text][0][1].text == "Some text"

def test_fields_from_format_labeled_precedence():
    # Label should take precedence over order
    fmt_labeled = {field_name: '1', field_text: '9'}
    fmt_ordered = [field_text, field_name] # Text first in order

    # Field has label '1' (name)
    src_text = "1Grizzly Bears"
    parsed, valid, fields = fields_from_format(src_text, fmt_ordered, fmt_labeled, '|')

    # Even though it's the first field (which would be text by order),
    # the label says it's name.
    assert field_name in fields
    assert fields[field_name][0][1] == "Grizzly Bears"
    assert field_text not in fields

def test_fields_from_format_unlabeled_fallthrough():
    # If no label matches, it should fall back to order
    fmt_labeled = {field_name: '1'}
    fmt_ordered = [field_text]
    src_text = "deals 5 damage." # '5' is not a label here

    parsed, valid, fields = fields_from_format(src_text, fmt_ordered, fmt_labeled, '|')

    assert fields[field_text][0][1].text == "deals 5 damage."

def test_card_integration_labeled_parsing():
    # Integration test using the Card class
    # Default labels: 1=name, 9=text, 5=types, etc.

    # Digit '9' in the middle of text should NOT be stripped.
    encoded = "5creature|||||deals 9 damage.|{}|N|1golem"
    card = Card(encoded)

    assert card.name == "golem"
    assert card.types == ["creature"]
    assert card.text.text == "deals 9 damage."
