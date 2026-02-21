import pytest
import os
import sys
import json
from io import StringIO

# Add lib to path
libdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../lib')
sys.path.append(libdir)
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/..')

import decode
import cardlib

def test_decklist_aggregation():
    # Setup some test cards with duplicates
    card_data = [
        {"name": "Black Lotus", "setCode": "LEA", "number": "232"},
        {"name": "Black Lotus", "setCode": "LEA", "number": "232"},
        {"name": "Island", "setCode": "ZEN", "number": "234"},
        {"name": "Island", "setCode": "ZEN", "number": "235"}, # Different number
        {"name": "Mox Emerald", "setCode": "LEA"}, # No number
        {"name": "Custom Card"}, # No set or number
    ]

    cards = [cardlib.Card(c) for c in card_data]

    # Capture stdout
    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()

    try:
        # We need to mock jdecode.mtg_open_file or just call decode.main with pre-loaded cards
        # But decode.main calls mtg_open_file internally.
        # So let's mock jdecode.mtg_open_file.
        import jdecode
        original_mtg_open_file = jdecode.mtg_open_file
        jdecode.mtg_open_file = lambda *args, **kwargs: cards

        decode.main("-", deck_out=True, verbose=False, quiet=True)

        jdecode.mtg_open_file = original_mtg_open_file
    finally:
        sys.stdout = old_stdout

    output = mystdout.getvalue()
    lines = output.strip().split('\n')

    assert "2 Black Lotus (LEA) 232" in lines
    assert "1 Island (ZEN) 234" in lines
    assert "1 Island (ZEN) 235" in lines
    assert "1 Mox Emerald (LEA)" in lines
    assert "1 Custom Card" in lines
    assert len(lines) == 5

def test_decklist_autoformat(tmp_path):
    # Test extension detection
    d = tmp_path / "subdir"
    d.mkdir()
    deck_file = d / "test.deck"

    # We'll use a real file but mock the loading to be fast
    import jdecode
    original_mtg_open_file = jdecode.mtg_open_file
    jdecode.mtg_open_file = lambda *args, **kwargs: [cardlib.Card({"name": "Black Lotus", "setCode": "LEA"})]

    try:
        # Pass oname so it detects .deck
        decode.main("-", oname=str(deck_file), verbose=False, quiet=True)
    finally:
        jdecode.mtg_open_file = original_mtg_open_file

    assert deck_file.exists()
    content = deck_file.read_text()
    assert "1 Black Lotus (LEA)" in content
