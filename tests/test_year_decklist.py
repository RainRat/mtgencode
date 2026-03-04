import pytest
import os
import sys

# Add lib to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)

import jdecode

def test_parse_decklist_year_name(tmp_path):
    """Test that card names starting with a year are correctly parsed when count is omitted."""
    deck_content = "1996 World Champion\n4 Grizzly Bears"
    deck_file = tmp_path / "deck.txt"
    deck_file.write_text(deck_content)

    res = jdecode.parse_decklist(str(deck_file))

    # Bug: res['world champion'] == 1996
    # Expected: res['1996 world champion'] == 1
    assert "1996 world champion" in res
    assert res["1996 world champion"] == 1
    assert res["grizzly bears"] == 4

def test_parse_decklist_explicit_count_with_year(tmp_path):
    """Test that explicit counts are correctly parsed even if the name starts with a year."""
    deck_content = "1 1996 World Champion"
    deck_file = tmp_path / "deck.txt"
    deck_file.write_text(deck_content)

    res = jdecode.parse_decklist(str(deck_file))

    assert "1996 world champion" in res
    assert res["1996 world champion"] == 1
