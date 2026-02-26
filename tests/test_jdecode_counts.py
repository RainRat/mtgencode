import pytest
import io
import os
import sys
from lib import jdecode, cardlib, utils

def test_mtg_open_file_counts(tmp_path, capsys):
    # fmt_ordered_named = [name, types, supertypes, subtypes, loyalty, pt, text, cost, rarity] (9 fields)

    # 1. Valid card (Land - no PT/Loyalty required)
    # |name|types|supertypes|subtypes|loyalty|pt|text|cost|rarity|
    valid_card = "|Valid Land|land|basic||||some text|||"
    # 2. Invalid card (Creature without P/T)
    invalid_card = "|Invalid Card|creature|||||some text|||"
    # 3. Unparsed card (Extra field - 10 fields)
    unparsed_card = "|Unparsed|creature|||||text|||EXTRA|"

    sep = utils.cardsep
    test_content = valid_card + sep + invalid_card + sep + unparsed_card

    d = tmp_path / "test_counts.txt"
    with open(d, 'w', encoding='utf-8', newline='\n') as f:
        f.write(test_content)

    # We need to use verbose=True to get the summary in stderr
    cards = jdecode.mtg_open_file(str(d), verbose=True, fmt_ordered=cardlib.fmt_ordered_named)

    captured = capsys.readouterr()

    assert "1 valid" in captured.err
    assert "1 invalid" in captured.err
    assert "1 failed to parse" in captured.err

def test_mtg_open_file_counts_no_double_count(tmp_path, capsys):
    # Test specifically for the double counting of invalid cards as unparsed when no report file is present
    invalid_card = "|Invalid|creature|||||text|||"

    d = tmp_path / "test_invalid.txt"
    with open(d, 'w', encoding='utf-8', newline='\n') as f:
        f.write(invalid_card)

    jdecode.mtg_open_file(str(d), verbose=True, fmt_ordered=cardlib.fmt_ordered_named)
    captured = capsys.readouterr()

    assert "1 invalid" in captured.err
    assert "0 failed to parse" in captured.err
