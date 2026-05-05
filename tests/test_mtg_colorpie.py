import pytest
import sys
import os
import json
from io import StringIO
from unittest.mock import patch, MagicMock

# Add lib and scripts directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

import scripts.mtg_colorpie as mtg_colorpie
import lib.cardlib as cardlib
import lib.utils as utils

@pytest.fixture
def sample_cards():
    """Returns a list of sample Card objects for testing."""
    cards_data = [
        {
            'name': 'White Flyer',
            'manaCost': '{1}{W}',
            'types': ['Creature'],
            'subtypes': ['Bird'],
            'text': 'Flying',
            'rarity': 'common'
        },
        {
            'name': 'Blue Flyer',
            'manaCost': '{U}',
            'types': ['Creature'],
            'subtypes': ['Faerie'],
            'text': 'Flying',
            'rarity': 'common'
        },
        {
            'name': 'Green Trampler',
            'manaCost': '{1}{G}',
            'types': ['Creature'],
            'subtypes': ['Beast'],
            'text': 'Trample',
            'rarity': 'common'
        },
        {
            'name': 'Artifact Creature',
            'manaCost': '{3}',
            'types': ['Artifact', 'Creature'],
            'subtypes': ['Golem'],
            'text': 'Trample',
            'rarity': 'uncommon'
        },
        {
            'name': 'Gold Card',
            'manaCost': '{W}{U}',
            'types': ['Instant'],
            'text': 'Flying\nDraw a card.',
            'rarity': 'rare'
        }
    ]
    return [cardlib.Card(c) for c in cards_data]

def test_get_color_category(sample_cards):
    """Verifies color categorization logic."""
    # White Flyer (W)
    assert mtg_colorpie.get_color_category(sample_cards[0]) == 'W'
    # Blue Flyer (U)
    assert mtg_colorpie.get_color_category(sample_cards[1]) == 'U'
    # Green Trampler (G)
    assert mtg_colorpie.get_color_category(sample_cards[2]) == 'G'
    # Artifact Creature (C)
    assert mtg_colorpie.get_color_category(sample_cards[3]) == 'C'
    # Gold Card (M)
    assert mtg_colorpie.get_color_category(sample_cards[4]) == 'M'

@patch('scripts.mtg_colorpie.jdecode.mtg_open_file')
@patch('sys.stdout', new_callable=StringIO)
def test_main_table_output(mock_stdout, mock_open_file, sample_cards):
    """Verifies the table output format and content."""
    mock_open_file.return_value = sample_cards

    with patch('sys.argv', ['mtg_colorpie.py', 'dummy.json']):
        mtg_colorpie.main()

    output = mock_stdout.getvalue()
    assert "MECHANICAL COLOR PI ANALYSIS" in output
    assert "Flying" in output
    assert "Trample" in output
    assert "Draw A Card" in output
    assert "CARD COUNT" in output
    assert "Total" in output

@patch('scripts.mtg_colorpie.jdecode.mtg_open_file')
@patch('sys.stdout', new_callable=StringIO)
def test_main_json_output(mock_stdout, mock_open_file, sample_cards):
    """Verifies the JSON output format."""
    mock_open_file.return_value = sample_cards

    with patch('sys.argv', ['mtg_colorpie.py', 'dummy.json', '--json']):
        mtg_colorpie.main()

    output = mock_stdout.getvalue()
    data = json.loads(output)

    assert data['total_cards'] == 5
    assert data['color_totals']['W'] == 1
    assert data['color_totals']['U'] == 1
    assert data['color_totals']['G'] == 1
    assert data['color_totals']['C'] == 1
    assert data['color_totals']['M'] == 1

    assert 'Flying' in data['matrix']
    assert data['matrix']['Flying']['W'] == 1
    assert data['matrix']['Flying']['U'] == 1
    assert data['matrix']['Flying']['M'] == 1
    assert 'W' not in data['matrix']['Trample']
    assert data['matrix']['Trample']['G'] == 1
    assert data['matrix']['Trample']['C'] == 1

@patch('scripts.mtg_colorpie.jdecode.mtg_open_file')
@patch('sys.stdout', new_callable=StringIO)
@patch('os.path.exists')
def test_main_filtering_propagation(mock_exists, mock_stdout, mock_open_file, sample_cards):
    """Verifies that CLI flags are correctly passed to mtg_open_file."""
    mock_open_file.return_value = sample_cards
    mock_exists.return_value = True # Ensure 'dummy.json' is treated as a file

    with patch('sys.argv', ['mtg_colorpie.py', 'dummy.json', '--set', 'MOM', '--rarity', 'rare']):
        mtg_colorpie.main()

    mock_open_file.assert_called_with(
        'dummy.json',
        verbose=False,
        grep=None,
        sets=['MOM'],
        rarities=['rare'],
        colors=None,
        identities=None,
        cmcs=None,
        mechanics=None,
        shuffle=False,
        seed=None
    )

@patch('scripts.mtg_colorpie.jdecode.mtg_open_file')
@patch('sys.stdout', new_callable=StringIO)
@patch('sys.stderr', new_callable=StringIO)
def test_empty_results(mock_stderr, mock_stdout, mock_open_file):
    """Verifies behavior when no cards are found."""
    mock_open_file.return_value = []

    with patch('sys.argv', ['mtg_colorpie.py', 'dummy.json']):
        mtg_colorpie.main()

    # Error message goes to stderr
    assert "No cards found matching the criteria." in mock_stderr.getvalue()
