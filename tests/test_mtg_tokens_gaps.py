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
    text = "Create a 1/1 white Soldier creature token."
    tokens = cardlib.extract_tokens_from_text(text)
    assert len(tokens) == 1
    assert tokens[0]['name'] == "1/1 White Soldier Token"
    assert tokens[0]['pt'] == "1/1"
    assert tokens[0]['color'] == "White"
    assert tokens[0]['type'] == "Soldier Creature"

def test_extract_tokens_creature_multi_color():
    # Tests the fix for "white and blue"
    text = "Create a 1/1 white and blue Spirit creature token."
    tokens = cardlib.extract_tokens_from_text(text)
    assert len(tokens) == 1
    assert tokens[0]['name'] == "1/1 White, Blue Spirit Token"
    assert tokens[0]['color'] == "White, Blue"
    assert tokens[0]['type'] == "Spirit Creature"

def test_extract_tokens_creature_with_abilities():
    text = "Create a 3/3 green Beast creature token with trample."
    tokens = cardlib.extract_tokens_from_text(text)
    assert len(tokens) == 1
    assert tokens[0]['name'] == "3/3 Green Beast Token"
    assert tokens[0]['abilities'] == "trample"

def test_extract_tokens_multiple_subtypes():
    text = "Create a 3/3 colorless Phyrexian Golem creature token."
    tokens = cardlib.extract_tokens_from_text(text)
    assert len(tokens) == 1
    assert tokens[0]['name'] == "3/3 Colorless Phyrexian Golem Token"
    assert tokens[0]['type'] == "Phyrexian Golem Creature"

def test_extract_tokens_named_treasure():
    text = "Create a Treasure token."
    tokens = cardlib.extract_tokens_from_text(text)
    assert len(tokens) == 1
    assert tokens[0]['name'] == "Treasure Token"
    assert "Sacrifice this artifact" in tokens[0]['abilities']

def test_extract_tokens_named_food():
    text = "Create two Food tokens."
    tokens = cardlib.extract_tokens_from_text(text)
    assert len(tokens) == 1
    assert tokens[0]['name'] == "Food Token"
    assert "gain 3 life" in tokens[0]['abilities']

def test_extract_tokens_named_clue():
    text = "Create a Clue token."
    tokens = cardlib.extract_tokens_from_text(text)
    assert len(tokens) == 1
    assert tokens[0]['name'] == "Clue Token"
    assert "Draw a card" in tokens[0]['abilities']

@patch('scripts.mtg_analyze.jdecode.mtg_open_file')
@patch('sys.stdout', new_callable=StringIO)
def test_mtg_tokens_main_json(mock_stdout, mock_open_file):
    # Mock card data
    mock_card = MagicMock(spec=cardlib.Card)
    mock_card.name = "Test Card"
    mock_card.tokens = [{'name': "1/1 White Soldier Token", 'pt': "1/1", 'color': "White", 'type': "Soldier Creature", 'abilities': ""}]
    mock_open_file.return_value = [mock_card]

    with patch('sys.argv', ['mtg_analyze.py', 'tokens', 'dummy.json', '--json']):
        mtg_analyze.main()

    output = mock_stdout.getvalue()
    data = json.loads(output)
    assert len(data) == 1
    assert data[0]['name'] == "1/1 White Soldier Token"

@patch('scripts.mtg_analyze.jdecode.mtg_open_file')
@patch('sys.stdout', new_callable=StringIO)
def test_mtg_tokens_main_table(mock_stdout, mock_open_file):
    # Mock card data
    mock_card = MagicMock(spec=cardlib.Card)
    mock_card.name = "Test Card"
    mock_card.tokens = [{'name': "1/1 White Soldier Token", 'pt': "1/1", 'color': "White", 'type': "Soldier Creature", 'abilities': ""}]
    mock_open_file.return_value = [mock_card]

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
    mock_card.tokens = []
    mock_open_file.return_value = [mock_card]

    with patch('sys.argv', ['mtg_analyze.py', 'tokens', 'dummy.json']):
        mtg_analyze.main()

    assert "No token definitions found" in mock_stdout.getvalue()

@patch('scripts.mtg_analyze.jdecode.mtg_open_file')
@patch('sys.stdout', new_callable=StringIO)
def test_mtg_tokens_main_duplicate_tokens(mock_stdout, mock_open_file):
    token = {'name': "1/1 White Soldier Token", 'pt': "1/1", 'color': "White", 'type': "Soldier Creature", 'abilities': ""}
    mock_card1 = MagicMock(spec=cardlib.Card)
    mock_card1.name = "Card 1"
    mock_card1.tokens = [token]

    mock_card2 = MagicMock(spec=cardlib.Card)
    mock_card2.name = "Card 2"
    mock_card2.tokens = [token]

    mock_open_file.return_value = [mock_card1, mock_card2]

    with patch('sys.argv', ['mtg_analyze.py', 'tokens', 'dummy.json']):
        mtg_analyze.main()

    output = mock_stdout.getvalue()
    # Check that count is 2 in the table
    assert "2" in output

@patch('scripts.mtg_analyze.jdecode.mtg_open_file')
@patch('sys.stdout', new_callable=StringIO)
def test_mtg_tokens_main_verbose(mock_stdout, mock_open_file):
    mock_card = MagicMock(spec=cardlib.Card)
    mock_card.name = "Test Card"
    mock_card.tokens = [{'name': "1/1 White Soldier Token", 'pt': "1/1", 'color': "White", 'type': "Soldier Creature", 'abilities': ""}]
    mock_open_file.return_value = [mock_card]

    with patch('sys.argv', ['mtg_analyze.py', 'tokens', 'dummy.json', '--verbose']):
        mtg_analyze.main()

    output = mock_stdout.getvalue()
    assert "Processing card: Test Card" in output
    assert "Found 1 tokens" in output

@patch('scripts.mtg_analyze.jdecode.mtg_open_file')
@patch('sys.stdout', new_callable=StringIO)
def test_mtg_tokens_main_color_force(mock_stdout, mock_open_file):
    mock_card = MagicMock(spec=cardlib.Card)
    mock_card.name = "Test Card"
    mock_card.tokens = [{'name': "1/1 White Soldier Token", 'pt': "1/1", 'color': "White", 'type': "Soldier Creature", 'abilities': ""}]
    mock_open_file.return_value = [mock_card]

    with patch('sys.argv', ['mtg_analyze.py', 'tokens', 'dummy.json', '--color']):
        mtg_analyze.main()

    output = mock_stdout.getvalue()
    assert "\x1b[" in output
