import sys
import os
import json
from unittest.mock import patch, MagicMock
from io import StringIO

# Add lib directory to path
libdir = os.path.join(os.getcwd(), 'lib')
if libdir not in sys.path:
    sys.path.append(libdir)

import scripts.mtg_analyze as mtg_analyze
import cardlib

def test_extract_tokens_creature_basic():
    c = cardlib.Card({'name': 'Test', 'types': ['Sorcery'], 'text': "Create a 1/1 white Soldier creature token."})
    tokens = c.tokens
    assert len(tokens) == 1
    assert tokens[0]['name'] == "1/1 White Soldier Token"
    assert tokens[0]['pt'] == "1/1"
    assert tokens[0]['color'] == "White"
    assert tokens[0]['type'] == "Soldier Creature"

def test_extract_tokens_creature_multi_color():
    # Tests the fix for "white and blue"
    c = cardlib.Card({'name': 'Test', 'types': ['Sorcery'], 'text': "Create a 1/1 white and blue Spirit creature token."})
    tokens = c.tokens
    assert len(tokens) == 1
    assert tokens[0]['name'] == "1/1 White, Blue Spirit Token"
    assert tokens[0]['color'] == "White, Blue"
    assert tokens[0]['type'] == "Spirit Creature"

def test_extract_tokens_creature_with_abilities():
    c = cardlib.Card({'name': 'Test', 'types': ['Sorcery'], 'text': "Create a 3/3 green Beast creature token with trample."})
    tokens = c.tokens
    assert len(tokens) == 1
    assert tokens[0]['name'] == "3/3 Green Beast Token"
    assert tokens[0]['abilities'] == "trample"

def test_extract_tokens_multiple_subtypes():
    c = cardlib.Card({'name': 'Test', 'types': ['Sorcery'], 'text': "Create a 3/3 colorless Phyrexian Golem creature token."})
    tokens = c.tokens
    assert len(tokens) == 1
    assert tokens[0]['name'] == "3/3 Colorless Phyrexian Golem Token"
    assert tokens[0]['type'] == "Phyrexian Golem Creature"

def test_extract_tokens_named_treasure():
    c = cardlib.Card({'name': 'Test', 'types': ['Sorcery'], 'text': "Create a Treasure token."})
    tokens = c.tokens
    assert len(tokens) == 1
    assert tokens[0]['name'] == "Treasure Token"
    assert "Sacrifice this artifact" in tokens[0]['abilities']

def test_extract_tokens_named_food():
    c = cardlib.Card({'name': 'Test', 'types': ['Sorcery'], 'text': "Create two Food tokens."})
    tokens = c.tokens
    assert len(tokens) == 1
    assert tokens[0]['name'] == "Food Token"
    assert "gain 3 life" in tokens[0]['abilities']

def test_extract_tokens_named_clue():
    c = cardlib.Card({'name': 'Test', 'types': ['Sorcery'], 'text': "Create a Clue token."})
    tokens = c.tokens
    assert len(tokens) == 1
    assert tokens[0]['name'] == "Clue Token"
    assert "Draw a card" in tokens[0]['abilities']

@patch('scripts.mtg_analyze.jdecode.mtg_open_file')
@patch('sys.stdout', new_callable=StringIO)
def test_mtg_tokens_main_json(mock_stdout, mock_open_file):
    # Use real card data for token extraction logic
    card = cardlib.Card({'name': 'Test Card', 'types': ['Sorcery'], 'text': "Create a 1/1 white Soldier creature token."})
    mock_open_file.return_value = [card]

    with patch('sys.argv', ['mtg_analyze.py', 'tokens', 'dummy.json', '--json']):
        mtg_analyze.main()

    output = mock_stdout.getvalue()
    data = json.loads(output)
    assert len(data) == 1
    assert data[0]['name'] == "1/1 White Soldier Token"

@patch('scripts.mtg_analyze.jdecode.mtg_open_file')
@patch('sys.stdout', new_callable=StringIO)
def test_mtg_tokens_main_table(mock_stdout, mock_open_file):
    card = cardlib.Card({'name': 'Test Card', 'types': ['Sorcery'], 'text': "Create a 1/1 white Soldier creature token."})
    mock_open_file.return_value = [card]

    with patch('sys.argv', ['mtg_analyze.py', 'tokens', 'dummy.json']):
        mtg_analyze.main()

    output = mock_stdout.getvalue()
    assert "EXTRACTED TOKENS" in output
    assert "Soldier Token" in output

@patch('scripts.mtg_analyze.jdecode.mtg_open_file')
@patch('sys.stdout', new_callable=StringIO)
def test_mtg_tokens_main_no_cards(mock_stdout, mock_open_file):
    mock_open_file.return_value = []

    with patch('sys.argv', ['mtg_analyze.py', 'tokens', 'dummy.json']):
        mtg_analyze.main()

    # Should print "No cards found" to stderr, let's just check it doesn't crash
    # and stdout is empty or doesn't have the header
    assert "EXTRACTED TOKENS" not in mock_stdout.getvalue()

@patch('scripts.mtg_analyze.jdecode.mtg_open_file')
@patch('sys.stdout', new_callable=StringIO)
def test_mtg_tokens_main_no_tokens(mock_stdout, mock_open_file):
    mock_card = MagicMock(spec=cardlib.Card)
    mock_card.name = "Test Card"
    mock_card.get_text.return_value = "No tokens here."
    mock_open_file.return_value = [mock_card]

    with patch('sys.argv', ['mtg_analyze.py', 'tokens', 'dummy.json']):
        mtg_analyze.main()

    assert "No token definitions found" in mock_stdout.getvalue()

@patch('scripts.mtg_analyze.jdecode.mtg_open_file')
@patch('sys.stdout', new_callable=StringIO)
def test_mtg_tokens_main_duplicate_tokens(mock_stdout, mock_open_file):
    mock_card1 = cardlib.Card({'name': 'Card 1', 'types': ['Sorcery'], 'text': "Create a 1/1 white Soldier creature token."})
    mock_card2 = cardlib.Card({'name': 'Card 2', 'types': ['Sorcery'], 'text': "Create a 1/1 white Soldier creature token."})

    mock_open_file.return_value = [mock_card1, mock_card2]

    with patch('sys.argv', ['mtg_analyze.py', 'tokens', 'dummy.json']):
        mtg_analyze.main()

    output = mock_stdout.getvalue()
    # Check that count is 2 in the table
    assert "2" in output

@patch('scripts.mtg_analyze.jdecode.mtg_open_file')
@patch('sys.stdout', new_callable=StringIO)
def test_mtg_tokens_main_verbose(mock_stdout, mock_open_file):
    mock_card = cardlib.Card({'name': 'Test Card', 'types': ['Sorcery'], 'text': "Create a 1/1 white Soldier creature token."})
    mock_open_file.return_value = [mock_card]

    with patch('sys.argv', ['mtg_analyze.py', 'tokens', 'dummy.json', '--verbose']):
        mtg_analyze.main()

    output = mock_stdout.getvalue()
    # The Card class stores names in lowercase internally.
    assert "Processing card: test card" in output
    assert "Found 1 tokens" in output

@patch('scripts.mtg_analyze.jdecode.mtg_open_file')
@patch('sys.stdout', new_callable=StringIO)
def test_mtg_tokens_main_color_force(mock_stdout, mock_open_file):
    mock_card = cardlib.Card({'name': 'Test Card', 'types': ['Sorcery'], 'text': "Create a 1/1 white Soldier creature token."})
    mock_open_file.return_value = [mock_card]

    with patch('sys.argv', ['mtg_analyze.py', 'tokens', 'dummy.json', '--color']):
        mtg_analyze.main()

    output = mock_stdout.getvalue()
    assert "\x1b[" in output
